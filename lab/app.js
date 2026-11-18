/* Лаборатория GEO STORY v2 — данные покадрово генерирует Blender 5.3.0 */
const D = {};
const $ = (s) => document.querySelector(s);
const el = (id) => document.getElementById(id);
const n = (v, d = 3) => (typeof v === 'number' ? v.toFixed(d) : '—');
const vec = (v) => (v ? v.map((x) => n(x)).join(', ') : '—');
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const card = (k, v, p) => `<div class="card"><div class="k">${esc(k)}</div><div class="big">${v}</div><p>${p}</p></div>`;

async function jget(p) {
  const r = await fetch(p);
  if (!r.ok) throw new Error(p + ' → ' + r.status);
  return r.json();
}
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
  $('#topstats').innerHTML = `<b>Blender ${esc(m.blender)}</b> · ${esc(s.engine)} · ${s.fps} fps · кадры ${s.start}–${s.end} · ${s.resolution[0]}×${s.resolution[1]} · ${m.objects_count} объектов · ${m.fcurves.length} F-кривых`;
  renderOverview(); renderFrames(); renderPaths(); renderRig();
  renderPrinciples(); renderChecks(); renderImages(); renderSources(); bindTabs();
}

function totalBones() {
  return Object.values(D.meta.rigs).reduce((a, r) => a + r.bones.length, 0);
}
function totalSkinned() {
  return Object.values(D.meta.rigs).reduce((a, r) => a + r.skinned_meshes.length, 0);
}
function passCount() { return D.qa.checks.filter((c) => c.pass).length; }
function shotFor(f) {
  let out = D.meta.story[0];
  for (const s of D.meta.story) if (s.frame <= f) out = s;
  return out;
}

/* ---------------- Обзор ---------------- */
function renderOverview() {
  const m = D.meta, s = m.scene, a = m.arch, q = passCount();
  const cards = [
    ['Blender', esc(m.blender), 'точная версия из релиза install'],
    ['Кадров', s.end - s.start + 1, `${s.duration_seconds} с при ${s.fps} fps`],
    ['Разрешение', `${s.resolution[0]}×${s.resolution[1]}`, `${s.engine}, ${s.samples} сэмплов + деноуз`],
    ['Объектов', m.objects_count, 'позиции записаны на каждом кадре'],
    ['Костей', totalBones(), `${m.constraints.length} IK-констрейнтов, 2 рига`],
    ['Привязано мешей', totalSkinned(), 'skinned mesh + визуализаторы костей'],
    ['F-кривых', m.fcurves.length, 'BEZIER / AUTO_CLAMPED + CONSTANT для срезов'],
    ['Проверок', `${q}/${D.qa.checks.length}`, q === D.qa.checks.length ? 'все зелёные' : 'есть замечания'],
  ];
  el('overview').innerHTML = `
    <h1>Красный идёт в гости к Синему</h1>
    <div class="sub">Полная замена первого «Гео-цирка»: два разных дома, два робота с разными лицами, походка по дорожке, окно, стук, подарок и хлопушка. Арка <b>развёрнута по оси +X</b> и робот проходит <b>сквозь</b> неё, а не рядом.</div>
    <div class="grid">${cards.map(([k,v,p]) => card(k,v,p)).join('')}</div>
    <h2>Сюжет по кадрам</h2>
    <div class="card"><p>${m.story.map(s => `<b>${s.frame}</b> · ${esc(s.name)} (камера ${esc(s.camera)})`).join('<br>')}</p></div>
    <h2>Главная геометрическая проверка</h2>
    <div class="card mono">ARCH center=${vec(a.center)} rotation=${vec(a.rotation)} hole_axis=${esc(a.hole_axis)} inner=${n(a.inner,2)} cross_frame=${a.cross_frame} robot_max_radius=${n(a.robot_max_radius,3)} passes_through=${a.passes_through ? 'TRUE' : 'FALSE'}</div>
    <h2>Файлы</h2>
    <div class="grid">
      ${card('Видео', `<a href="../${esc(m.output.mp4)}">${esc(m.output.mp4)}</a>`, 'H.264, 240 кадров')}
      ${card('Сцена', `<a href="../${esc(m.output.blend)}">${esc(m.output.blend)}</a>`, 'открывается в Blender 5.3.0')}
      ${card('Раскадровка', '<a href="../renders/v2/screenshots/contact_sheet.png">contact_sheet.png</a>', '13 ключевых кадров')}
      ${card('Архив кадров', `<a href="../${esc(m.output.frame_archive)}">${esc(m.output.frame_archive)}</a>`, '240 JPEG-кадров')}
    </div>
    <h2>Motion Paths</h2><div class="card mono">${esc(JSON.stringify(m.motion_paths))}</div>`;
}

/* ---------------- Кадры ---------------- */
let curFrame = 1, timer = null;
function renderFrames() {
  const end = D.meta.scene.end;
  el('frames').innerHTML = `
    <h1>Все кадры, все позиции</h1>
    <div class="sub">Слайдер = покадровая проверка. Таблица показывает объекты и кости в мировых координатах на выбранном кадре.</div>
    <div class="framebox">
      <div>
        <img class="frameimg" id="frameimg" alt="кадр">
        <div style="margin-top:12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <button class="act" id="play">▶ Воспроизвести</button>
          <span id="flabel" class="mono"></span>
        </div>
        <input type="range" id="slider" min="1" max="${end}" value="1" style="margin-top:12px">
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
    else { timer = setInterval(() => setFrame((curFrame % end) + 1), 1000 / D.meta.scene.fps); el('play').textContent = '⏸ Пауза'; }
  });
  setFrame(1);
}
function setFrame(f) {
  curFrame = f;
  const end = D.meta.scene.end;
  el('frameimg').src = `../renders/v2/frames_preview/frame_${String(f).padStart(4,'0')}.jpg`;
  el('slider').value = f;
  const fr = D.anim.frames[f - 1], shot = shotFor(f);
  el('flabel').textContent = `кадр ${String(f).padStart(3,'0')} / ${end} · t=${((f-1)/D.meta.scene.fps).toFixed(2)}s · ${fr.camera} · ${shot.name}`;
  el('tlabel').textContent = f;
  const c = fr.deformed_centers || {};
  const bits = [
    ['Красный', c['Red_Body']], ['Синий', c['Blue_Body']],
    ['Подарок', c['GiftBox_Base']], ['Дверь красного', c['RedHouse_Door']],
    ['Дверь синего', c['BlueHouse_Door']], ['Активная камера', fr.camera]
  ];
  el('fstats').innerHTML = bits.map(([k,v]) => `<div class="card"><div class="k">${esc(k)}</div><div class="mono" style="margin-top:6px">${typeof v === 'string' ? esc(v) : vec(v)}</div></div>`).join('');
  fillTable(f);
}
function fillTable(f) {
  const fr = D.anim.frames[f - 1];
  const q = (el('filter').value || '').toLowerCase();
  let rows = '<thead><tr><th>тип</th><th>имя</th><th>X</th><th>Y</th><th>Z</th><th>масштаб</th></tr></thead><tbody>';
  const add = (type, name, loc, scale) => {
    if (q && !name.toLowerCase().includes(q)) return;
    rows += `<tr><td>${type}</td><td class="mono">${esc(name)}</td><td>${n(loc[0])}</td><td>${n(loc[1])}</td><td>${n(loc[2])}</td><td>${scale ? vec(scale) : '—'}</td></tr>`;
  };
  for (const [name, o] of Object.entries(fr.objects || {})) add('obj', name, o.location, o.scale);
  for (const [name, b] of Object.entries(fr.bones || {})) add('bone', name, b.head, b.scale);
  rows += '</tbody>';
  el('postable').innerHTML = rows;
}

/* ---------------- Траектории / QA ---------------- */
function renderPaths() {
  const q = D.qa;
  el('paths').innerHTML = `
    <h1>Траектории, арка и геометрия</h1>
    <div class="sub">Графики и диагностические рендеры собраны из тех же данных, что использует Blender.</div>
    <div class="grid">
      ${card('Скорости', `<span class="mono">${esc(JSON.stringify(q.max_speed || {}))}</span>`, 'максимум по кадрам')}
      ${card('Ускорения', `<span class="mono">${esc(JSON.stringify(q.max_accel || {}))}</span>`, 'максимум по кадрам')}
      ${card('Камеры', `<span class="mono">${esc(JSON.stringify(q.cameras || {}))}</span>`, 'покрытие 240 кадров')}
      ${card('Арка', `f${D.meta.arch.cross_frame}`, `${n(D.meta.arch.robot_max_radius,3)} &lt; ${n(D.meta.arch.inner,2)}`)}
    </div>
    <div class="grid" style="margin-top:14px">
      <div class="card"><div class="k">График X / кадр + сечение арки</div><img src="../renders/v2/screenshots/qa_trajectory.png" style="width:100%;margin-top:8px"></div>
      <div class="card"><div class="k">Проход сквозь арку (вид по оси +X)</div><img src="../renders/v2/screenshots/arch_pass.png" style="width:100%;margin-top:8px"></div>
      <div class="card"><div class="k">Скелет</div><img src="../renders/v2/screenshots/skeleton.png" style="width:100%;margin-top:8px"></div>
      <div class="card"><div class="k">Motion Paths</div><img src="../renders/v2/screenshots/motion_paths.png" style="width:100%;margin-top:8px"></div>
    </div>`;
}

/* ---------------- Скелет ---------------- */
function renderRig() {
  const m = D.meta;
  let html = `<h1>Два скелета, IK и веса</h1><div class="sub">Red и Blue: ${totalBones()} костей суммарно, ${m.constraints.length} IK-констрейнтов, ${m.bone_visualizers.length} визуализаторов костей, ${totalSkinned()} привязанных мешей.</div><div class="grid">`;
  for (const [tag, r] of Object.entries(m.rigs)) {
    html += card(tag + ' риг', `${r.bones.length} костей / ${r.skinned_meshes.length} мешей`, 'shape keys: blink, happy, open mouth; брови, зрачки, антенна');
  }
  html += '</div><h2>IK-констрейнты</h2><div class="card mono">' + m.constraints.map(c => `${c.rig}.${c.bone} → ${c.subtarget} (${c.type}, chain ${c.chain_count})`).join('<br>') + '</div>';
  for (const [tag, r] of Object.entries(m.rigs)) {
    html += `<h2>${esc(tag)} — кости</h2><div class="scroll"><table><thead><tr><th>имя</th><th>родитель</th><th>head</th><th>tail</th><th>deform</th></tr></thead><tbody>`;
    for (const b of r.bones) html += `<tr><td class="mono">${esc(b.name)}</td><td>${esc(b.parent || '—')}</td><td>${vec(b.head)}</td><td>${vec(b.tail)}</td><td>${b.deform ? 'да' : 'нет'}</td></tr>`;
    html += '</tbody></table></div>';
  }
  el('rig').innerHTML = html;
}

/* ---------------- Принципы ---------------- */
function renderPrinciples() {
  el('principles').innerHTML = `<h1>12 принципов анимации в этой сцене</h1><div class="sub">Исследованные источники применены к походке, эмоциям, камере и рендеру.</div><div class="grid">` +
    D.meta.principles.map((p,i) => card(`${i+1}. ${p.name}`, esc(p.where), 'применено в GEO STORY v2')).join('') + '</div>';
}

/* ---------------- Проверки ---------------- */
function renderChecks() {
  const checks = D.qa.checks.map(c => `<div class="card" style="border-left:5px solid ${c.pass ? '#54d98c' : '#f05a5a'}"><div class="k">${c.pass ? 'PASS' : 'FAIL'}</div><p><b>${esc(c.name)}</b><br><span class="mono">${esc(c.detail)}</span></p></div>`).join('');
  const interp = {};
  for (const f of D.meta.fcurves) interp[f.path] = (interp[f.path] || 0) + 1;
  el('checks').innerHTML = `
    <h1>Автоматические проверки: ${passCount()}/${D.qa.checks.length}</h1>
    <div class="grid">${checks}</div>
    <h2>F-кривые</h2>
    <div class="card mono">${D.meta.fcurves.length} каналов · ${esc(JSON.stringify(interp))}</div>
    <h2>Motion Paths</h2><div class="card mono">${esc(JSON.stringify(D.meta.motion_paths))}</div>
    <h2>Первые 60 каналов</h2><div class="scroll"><table><thead><tr><th>объект</th><th>путь</th><th>индекс</th><th>ключей</th></tr></thead><tbody>` +
    D.meta.fcurves.slice(0,60).map(f => `<tr><td class="mono">${esc(f.id)}</td><td class="mono">${esc(f.path)}</td><td>${f.index}</td><td>${f.keys}</td></tr>`).join('') + '</tbody></table></div>';
}

/* ---------------- Изображения ---------------- */
function renderImages() {
  const keys = [1,18,30,54,89,100,129,150,169,186,205,220,240];
  const diagnostics = ['contact_sheet.png','all_frames.png','qa_trajectory.png','arch_pass.png','skeleton.png','motion_paths.png','diagnostics.png'];
  const shot = (file, label) => `<div class="card"><div class="k">${esc(label)}</div><a href="../renders/v2/screenshots/${file}" target="_blank"><img src="../renders/v2/screenshots/${file}" style="width:100%;margin-top:8px"></a></div>`;
  el('images').innerHTML = `<h1>Изображения и скриншот-проверки</h1><div class="sub">Все ключевые кадры отрендерены Cycles CPU и проверены визуально.</div><div class="grid">` +
    keys.map(f => shot(`frame_${String(f).padStart(4,'0')}.png`, `кадр ${f}`)).join('') +
    diagnostics.map(f => shot(f, f)).join('') + '</div>';
}

/* ---------------- Источники ---------------- */
function renderSources() {
  el('sources').innerHTML = `<h1>Источники и установщик</h1><div class="sub">Исследование риггинга, траекторий, Motion Paths и качества рендера.</div><div class="grid">` +
    D.meta.sources.map(s => `<div class="card"><div class="k">${esc(s.title)}</div><p>${esc(s.takeaway)}</p><p><a href="${esc(s.url)}" target="_blank">${esc(s.url)}</a></p></div>`).join('') +
    `</div><h2>Точный установщик Blender</h2><div class="card mono">${esc(D.meta.installer.url)}<br>${D.meta.installer.size} bytes<br>SHA-256 ${esc(D.meta.installer.sha256)}</div>`;
}

function bindTabs() {
  document.querySelectorAll('#nav button').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('#nav button').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    el(b.dataset.tab).classList.add('active');
  }));
}
init();
