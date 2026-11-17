/* Лаборатория «Гео-цирк» — читает данные, которые сгенерировал Blender 5.3.0 */
const D = {};
const $ = (s) => document.querySelector(s);
const el = (id) => document.getElementById(id);

async function jget(p) {
  const r = await fetch(p);
  if (!r.ok) throw new Error(p + ' → ' + r.status);
  return r.json();
}

const n = (v, d = 3) => (typeof v === 'number' ? v.toFixed(d) : '—');
const vec = (v) => (v ? v.map((x) => n(x)).join(', ') : '—');
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

async function init() {
  try {
    [D.meta, D.anim, D.traj, D.qa] = await Promise.all([
      jget('data/meta.json'), jget('data/animation.json'),
      jget('data/trajectories.json'), jget('data/qa.json')
    ]);
  } catch (e) {
    $('#topstats').textContent = 'Ошибка загрузки данных: ' + e.message;
    return;
  }
  const m = D.meta, s = m.scene;
  $('#topstats').innerHTML = `<b>${esc(m.blender)}</b> · ${esc(s.engine)} · ${s.fps} fps · кадры ${s.start}–${s.end} · ${s.resolution[0]}×${s.resolution[1]} · ${m.objects_count} объектов · ${m.rig.bones.length} костей · ${m.fcurves.length} F-кривых`;
  renderOverview();
  renderFrames();
  renderPaths();
  renderRig();
  renderPrinciples();
  renderChecks();
  renderImages();
  renderSources();
  bindTabs();
}

/* ---------------- Обзор ---------------- */
function renderOverview() {
  const m = D.meta, s = m.scene, q = D.qa;
  const pass = q.checks.filter((c) => c.pass).length;
  const cards = [
    ['Blender', esc(m.blender), 'установлен из релиза install'],
    ['Кадров', s.end - s.start + 1, `${s.duration_seconds} с при ${s.fps} fps`],
    ['Разрешение', `${s.resolution[0]}×${s.resolution[1]}`, `${s.engine}, ${s.samples} сэмплов + деноуз`],
    ['Объектов', m.objects_count, 'все позиции записаны покадрово'],
    ['Костей', m.rig.bones.length, `${m.rig.constraints.length} IK-констрейнта`],
    ['Привязано мешей', m.rig.skinned_meshes.length, '100% вес на одну кость'],
    ['F-кривых', m.fcurves.length, 'BEZIER + AUTO_CLAMPED'],
    ['Проверок', `${pass}/${q.checks.length}`, pass === q.checks.length ? 'все зелёные' : 'есть замечания'],
  ];
  el('overview').innerHTML = `
    <h1>Гео-цирк: лаборатория анимации</h1>
    <div class="sub">Небольшой мультфильм из геометрических фигур: куб-робот с настоящим скелетом прыгает через кольцо, шар отскакивает по дугам, конус удивляется, а сундук из <span class="mono">сундук.blend</span> открывается в финале.</div>
    <div class="grid">${cards.map(([k, v, p]) => `<div class="card"><div class="k">${k}</div><div class="big">${v}</div><p>${p}</p></div>`).join('')}</div>
    <h2>Что отслеживается постоянно</h2>
    <div class="card"><p>Каждый из ${s.end - s.start + 1} кадров: позиции/повороты/масштабы всех ${m.objects_count} объектов, головы и хвосты всех ${m.rig.bones.length} костей, деформированные центры 5 ключевых мешей, скорости и ускорения, траектории, F-кривые, Motion Paths Blender, результаты 11 автоматических проверок и все отрендеренные изображения. Данные — <span class="mono">lab/data/*.json</span>, картинки — <span class="mono">renders/</span>.</p></div>
    <h2>Файлы</h2>
    <div class="grid">
      <div class="card"><div class="k">Видео</div><p><a href="../geo_cartoon.mp4">geo_cartoon.mp4</a> · H.264</p></div>
      <div class="card"><div class="k">Сцена</div><p><a href="../geo_cartoon.blend">geo_cartoon.blend</a> · открывается в 5.3.0</p></div>
      <div class="card"><div class="k">Изображения</div><p><a href="../renders/screenshots/contact_sheet.png">раскадровка</a>, <a href="../renders/screenshots/skeleton.png">скелет</a>, <a href="../renders/screenshots/motion_paths.png">траектории</a></p></div>
      <div class="card"><div class="k">Установщик</div><p class="mono">${esc(m.installer.sha256.slice(0, 24))}…<br>SHA-256 совпал, 406 944 100 байт</p></div>
    </div>
    <h2>Статус Motion Paths</h2>
    <div class="card mono">${esc(JSON.stringify(m.motion_paths))}</div>`;
}

/* ---------------- Кадры ---------------- */
let curFrame = 1, timer = null;
function renderFrames() {
  el('frames').innerHTML = `
    <h1>Все кадры, все позиции</h1>
    <div class="sub">Слайдер = покадровая проверка. Таблица показывает и объекты, и кости в мировых координатах на выбранном кадре.</div>
    <div class="framebox">
      <div>
        <img class="frameimg" id="frameimg" src="../renders/frames/frame_0001.png" alt="кадр">
        <div style="margin-top:12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <button class="act" id="play">▶ Воспроизвести</button>
          <span id="flabel" class="mono">кадр 001 / 120 · t=0.00s</span>
        </div>
        <input type="range" id="slider" min="1" max="120" value="1" style="margin-top:12px">
        <div id="fstats" class="grid" style="margin-top:12px"></div>
      </div>
      <div>
        <h2 style="margin-top:0">Позиции кадра <span id="tlabel">1</span></h2>
        <input type="text" id="filter" placeholder="фильтр по имени…">
        <div class="scroll" style="margin-top:10px"><table id="postable"></table></div>
      </div>
    </div>`;
  el('slider').addEventListener('input', (e) => setFrame(+e.target.value));
  el('filter').addEventListener('input', () => fillTable(curFrame));
  el('play').addEventListener('click', () => {
    if (timer) { clearInterval(timer); timer = null; el('play').textContent = '▶ Воспроизвести'; }
    else { timer = setInterval(() => setFrame((curFrame % 120) + 1), 1000 / 24); el('play').textContent = '⏸ Пауза'; }
  });
  setFrame(1);
}
function setFrame(f) {
  curFrame = f;
  const img = `../renders/frames/frame_${String(f).padStart(4, '0')}.png`;
  el('frameimg').src = img;
  el('slider').value = f;
  el('flabel').textContent = `кадр ${String(f).padStart(3,'0')} / 120 · t=${((f-1)/24).toFixed(2)}s`;
  el('tlabel').textContent = f;
  const fr = D.anim.frames[f - 1];
  const c = fr.deformed_centers || {};
  const bits = [
    ['Куб (центр)', c['Hero_Body']], ['Шар', c['Ball_Sphere']],
    ['Кольцо', c['Torus_Hoop']], ['Конус', c['Cone_Grump']],
    ['Крышка сундука', c['Chest_Lid']], ['Root (голова кости)', fr.bones['Root'].head]
  ];
  el('fstats').innerHTML = bits.map(([k, v]) => `<div class="card"><div class="k">${k}</div><div class="mono" style="margin-top:6px">${vec(v)}</div></div>`).join('');
  fillTable(f);
}
function fillTable(f) {
  const fr = D.anim.frames[f - 1];
  const q = (el('filter').value || '').toLowerCase();
  let rows = '<thead><tr><th>тип</th><th>имя</th><th>X</th><th>Y</th><th>Z</th><th>масштаб</th></tr></thead><tbody>';
  const add = (type, name, p, sc) => {
    if (q && !(type + ' ' + name).toLowerCase().includes(q)) return;
    rows += `<tr><td>${type}</td><td class="bone">${esc(name)}</td><td>${n(p[0])}</td><td>${n(p[1])}</td><td>${n(p[2])}</td><td class="mono">${vec(sc)}</td></tr>`;
  };
  Object.entries(fr.objects).forEach(([k, v]) => add('obj', k, v.location, v.scale));
  Object.entries(fr.bones).forEach(([k, v]) => add('bone', k, v.head, v.scale));
  Object.entries(fr.deformed_centers || {}).forEach(([k, v]) => add('deform', k, v, [1,1,1]));
  el('postable').innerHTML = rows + '</tbody>';
}

/* ---------------- Траектории ---------------- */
const COLORS = {hero_root:'#ff7ab6', ball:'#62b6ff', cone:'#b98cff', torus:'#ffc861', chest_lid:'#64e6c0'};
const LABELS = {hero_root:'Куб (Root)', ball:'Шар', cone:'Конус', torus:'Кольцо', chest_lid:'Сундук'};
function svgChart(series, axis, title) {
  const all = series.flatMap((s) => s.pts.map((p) => p[1]));
  let lo = Math.min(...all), hi = Math.max(...all);
  if (hi - lo < 1e-6) hi = lo + 1;
  const W = 900, H = 170, P = 12;
  const x = (f) => P + ((f - 1) / 119) * (W - 2 * P);
  const y = (v) => H - P - ((v - lo) / (hi - lo)) * (H - 2 * P);
  let g = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;
  for (let i = 0; i <= 4; i++) {
    const yy = P + i * (H - 2*P) / 4;
    g += `<line x1="0" y1="${yy}" x2="${W}" y2="${yy}" stroke="#2b3560" stroke-width="1"/>`;
  }
  for (let f = 1; f <= 120; f += 24) {
    g += `<line x1="${x(f)}" y1="0" x2="${x(f)}" y2="${H}" stroke="#222b4d" stroke-width="1"/>`;
    g += `<text x="${x(f)+3}" y="${H-3}" fill="#6f7aa8" font-size="10">${f}</text>`;
  }
  series.forEach((s) => {
    const pts = s.pts.map((p) => `${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ');
    g += `<polyline points="${pts}" fill="none" stroke="${s.color}" stroke-width="2" stroke-linejoin="round"/>`;
  });
  g += `</svg><div class="legend">${series.map((s)=>`<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join('')}<span>диапазон ${n(lo,2)} … ${n(hi,2)}</span></div>`;
  return `<div class="chart"><h3 style="margin:0 0 6px">${title}</h3>${g}</div>`;
}
function renderPaths() {
  const keys = ['hero_root','ball','cone','torus','chest_lid'];
  const mk = (idx) => keys.map((k) => ({name:LABELS[k], color:COLORS[k], pts:D.traj[k].map((p)=>[p[0], p[idx]])}));
  const speeds = keys.map((k) => {
    const p = D.traj[k]; const v = [];
    for (let i = 1; i < p.length; i++) {
      const d = Math.hypot(p[i][1]-p[i-1][1], p[i][2]-p[i-1][2], p[i][3]-p[i-1][3]);
      v.push([p[i][0], d * 24]);
    }
    return {name:LABELS[k], color:COLORS[k], pts:v};
  });
  el('paths').innerHTML = `
    <h1>Траектории и Motion Paths</h1>
    <div class="sub">Каждая точка — реально вычисленная позиция в Blender на каждом кадре. Эти же данные запечены в видимые светящиеся ленты <span class="mono">Path_*</span> внутри сцены.</div>
    ${svgChart(mk(1), 'X', 'X по кадрам (движение по сцене)')}
    ${svgChart(mk(3), 'Z', 'Z по кадрам (прыжки, отскоки, полёт)')}
    ${svgChart(mk(2), 'Y', 'Y по кадрам (глубина)')}
    ${svgChart(speeds, 'V', 'Скорость, единиц/секунду')}
    <h2>Максимальные скорости</h2>
    <div class="scroll"><table><thead><tr><th>объект</th><th>max speed</th><th>max accel</th></tr></thead><tbody>
    ${Object.entries(D.qa.max_speed).map(([k,v])=>`<tr><td>${LABELS[k]||k}</td><td>${n(v,2)}</td><td>${n(D.qa.max_accel[k],2)}</td></tr>`).join('')}
    </tbody></table></div>`;
}

/* ---------------- Скелет ---------------- */
function renderRig() {
  const bones = D.meta.rig.bones;
  const byParent = {};
  bones.forEach((b) => { (byParent[b.parent || 'ROOT'] ||= []).push(b); });
  const tree = (p, depth) => (byParent[p] || []).map((b) => `<li><span class="bone">${esc(b.name)}</span>
      <span class="${b.deform?'deform':'nodeform'}">${b.deform?'deform':'IK / control'}</span>
      <span class="mono" style="color:var(--muted)">head ${vec(b.head)}</span>
      ${byParent[b.name] ? `<ul class="tree">${tree(b.name, depth+1)}</ul>` : ''}</li>`).join('');
  el('rig').innerHTML = `
    <h1>Скелет: 18 костей, 3 IK, 22 привязанных меша</h1>
    <div class="sub">Арматура <span class="mono">HeroRig</span>. Все части куба имеют вершинную группу с весом 1.0 и модификатор Armature — это настоящий skinning, а не простое движение объектов.</div>
    <div class="grid"><div class="card"><h3 style="margin-top:0">Иерархия костей</h3><ul class="tree">${tree('ROOT',0)}</ul></div>
    <div>
      <h2 style="margin-top:0">IK-констрейнты</h2>
      <div class="scroll"><table><thead><tr><th>кость</th><th>тип</th><th>цель</th><th>цепь</th><th>влияние</th></tr></thead><tbody>
      ${D.meta.rig.constraints.map((c)=>`<tr><td class="bone">${esc(c.bone)}</td><td>${c.type}</td><td class="bone">${esc(c.subtarget||'')}</td><td>${c.chain_count}</td><td>${n(c.influence,2)}</td></tr>`).join('')}
      </tbody></table></div>
      <h2>Визуализаторы костей</h2>
      <div class="card"><p>${D.meta.rig.bone_visualizers.length} эмиссионных цилиндров/сфер, скрытых в обычном рендере и показанных на скриншоте <a href="../renders/screenshots/skeleton.png">skeleton.png</a>.</p></div>
      <h2>Привязанные меши</h2>
      <div class="card mono" style="max-height:220px;overflow:auto">${D.meta.rig.skinned_meshes.map(esc).join('<br>')}</div>
    </div></div>`;
}

/* ---------------- Принципы ---------------- */
function renderPrinciples() {
  el('principles').innerHTML = `<h1>12 принципов анимации — где они в мультике</h1>
    <div class="sub">Собрано из исследованных источников (см. вкладку «Источники») и применено в коде <span class="mono">scripts/build_scene.py</span>.</div>
    <div class="grid">${D.meta.principles.map((p,i)=>`<div class="principle"><b>${i+1}. ${esc(p.name)}</b><small>${esc(p.where||'')}${p.note?' · '+esc(p.note):''}</small></div>`).join('')}</div>`;
}

/* ---------------- Проверки ---------------- */
function renderChecks() {
  el('checks').innerHTML = `<h1>Автоматические проверки и F-кривые</h1>
    <div class="sub">Считается в Blender на всех 120 кадрах: конечность координат, непрерывность дуг, сохранение объёма, достижимость IK, попадание в кадр.</div>
    <div class="grid">${D.qa.checks.map((c)=>`<div class="card"><span class="pill ${c.pass?'ok':'bad'}">${c.pass?'PASS':'FAIL'}</span><p style="margin-top:8px"><b>${esc(c.name)}</b><br>${esc(c.detail)}</p></div>`).join('')}</div>
    <h2>Сглаживание в Graph Editor (${D.meta.fcurves.length} F-кривых)</h2>
    <div class="card"><p>Blender 5.3 больше не имеет <span class="mono">Action.fcurves</span>; используется <span class="mono">bpy_extras.anim_utils.action_get_channelbag_for_slot(action, slot)</span>. Всем ключам выставлены BEZIER + AUTO_CLAMPED.</p></div>
    <div class="scroll" style="margin-top:12px"><table><thead><tr><th>ID</th><th>data_path</th><th>index</th><th>ключей</th><th>интерполяция</th></tr></thead><tbody>
    ${D.meta.fcurves.slice(0,400).map((f)=>`<tr><td>${esc(f.id)}</td><td class="mono">${esc(f.data_path)}</td><td>${f.index}</td><td>${f.keys}</td><td>${esc(f.interpolation)}</td></tr>`).join('')}
    </tbody></table></div>`;
}

/* ---------------- Изображения ---------------- */
function renderImages() {
  const shots = [
    ['contact_sheet.png','Раскадровка: 12 ключевых кадров'],
    ['skeleton.png','Скелет: кости и суставы (эмиссионные визуализаторы)'],
    ['motion_paths.png','Траектории: запеченные Motion Paths и маркеры ключей'],
    ['skeleton_overlay.png','Скелет поверх тела куба'],
    ['all_frames.png','Все 120 кадров одним изображением'],
  ];
  el('images').innerHTML = `<h1>Постоянные изображения / скриншот-верификация</h1>
    <div class="sub">Каждый кадр отрендерен в PNG и доступен здесь. Диагностические кадры сделаны тем же Blender 5.3.0.</div>
    ${shots.map(([f,t])=>`<h2>${t}</h2><img class="shot" src="../renders/screenshots/${f}" alt="${t}">`).join('')}
    <h2>Галерея всех кадров</h2><div class="gallery">
    ${Array.from({length:120},(_,i)=>`<a href="../renders/frames/frame_${String(i+1).padStart(4,'0')}.png" target="_blank"><img loading="lazy" src="../renders/frames/frame_${String(i+1).padStart(4,'0')}.png"><span>кадр ${String(i+1).padStart(3,'0')}</span></a>`).join('')}
    </div>`;
}

/* ---------------- Источники ---------------- */
function renderSources() {
  el('sources').innerHTML = `<h1>Исследование: ${D.meta.sources.length} источников</h1>
    <div class="sub">Кости/скелет, IK, траектории и Motion Paths, 12 принципов, Graph Editor, Eevee/Cycles quality, Blender 5.x Python API, FFMPEG.</div>
    ${D.meta.sources.map((s,i)=>`<div class="src"><b>${i+1}. ${esc(s.title)}</b> · <a href="${esc(s.url)}" target="_blank">открыть</a><p>${esc(s.takeaway)}</p></div>`).join('')}`;
}

function bindTabs() {
  document.querySelectorAll('#nav button').forEach((b) => b.addEventListener('click', () => {
    document.querySelectorAll('#nav button').forEach((x) => x.classList.remove('active'));
    document.querySelectorAll('.tab').forEach((x) => x.classList.remove('active'));
    b.classList.add('active');
    el(b.dataset.tab).classList.add('active');
  }));
}

init();
