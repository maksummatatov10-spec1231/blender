import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

/* ============================================================ strings */
const STR = {
  ru: {
    title: "СТРАННИК",
    sub: "Долина четырёх ветров",
    play: "Играть",
    settings: "Настройки",
    quit: "Выйти",
    settingsTitle: "Настройки",
    lang: "Язык",
    gfx: "Графика",
    back: "Назад",
    resume: "Продолжить",
    byeTitle: "До встречи",
    bye: "Горы будут ждать тебя.",
    loading: "Загрузка мира…",
    hint: "WASD — ходьба · Shift — бег · Пробел — прыжок · мышь — осмотр · V — вид 1/3 лицо · E — табличка · Esc — меню",
    close: "Закрыть",
    pressE: "E — прочитать",
    gfxNames: { low: "Низкая", medium: "Средняя", high: "Высокая", ultra: "Ультра" },
    loc: { valley: "Долина", village: "Деревня", forest: "Лес", mountain: "Горы", falls: "Водопад", lake: "Озеро" },
    compass: ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"],
    signs: {
      village: ["Деревня Тихий Дол", "Здесь пахнет дымом и хлебом. Жители ушли в поля, но двери открыты для путника."],
      forest: ["Старый лес", "Сосны здесь помнят первые тропы. Не сходи с пути, когда туман спускается с гор."],
      mountain: ["Предгорье", "Выше — только ветер и камни. Перевал закрыт снегом до самой весны."],
      falls: ["Серебряный водопад", "Вода падает с высоты тринадцати шагов. Говорят, если умыться ею, дорога станет легче."],
      lake: ["Озеро Тихое", "Самая глубокая вода долины. Рыбаки говорят, что на дне спит старый валун."],
    },
  },
  en: {
    title: "WANDERER",
    sub: "Valley of the Four Winds",
    play: "Play",
    settings: "Settings",
    quit: "Quit",
    settingsTitle: "Settings",
    lang: "Language",
    gfx: "Graphics",
    back: "Back",
    resume: "Resume",
    byeTitle: "See you",
    bye: "The mountains will wait for you.",
    loading: "Loading the world…",
    hint: "WASD — walk · Shift — run · Space — jump · mouse — look · V — 1st/3rd person · E — sign · Esc — menu",
    close: "Close",
    pressE: "E — read",
    gfxNames: { low: "Low", medium: "Medium", high: "High", ultra: "Ultra" },
    loc: { valley: "Valley", village: "Village", forest: "Forest", mountain: "Mountains", falls: "Waterfall", lake: "Lake" },
    compass: ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
    signs: {
      village: ["Quiet Dale Village", "It smells of smoke and bread here. The villagers are out in the fields, but the doors are open to travellers."],
      forest: ["The Old Forest", "These pines remember the first trails. Stay on the path when the fog rolls down from the mountains."],
      mountain: ["The Foothills", "Above there is only wind and stone. The pass is sealed with snow until spring."],
      falls: ["Silver Falls", "The water drops thirteen paces. They say washing your face here makes the road easier."],
      lake: ["Quiet Lake", "The deepest water in the valley. Fishermen say an old boulder sleeps at the bottom."],
    },
  },
};

/* ============================================================ presets */
const PRESETS = {
  low: { dpr: 1, shadows: false, shadowSize: 1024, trees: 70, grass: false, fogNear: 45, fogFar: 150 },
  medium: { dpr: 1, shadows: true, shadowSize: 1024, trees: 120, grass: false, fogNear: 60, fogFar: 190 },
  high: { dpr: 1.5, shadows: true, shadowSize: 2048, trees: 190, grass: true, fogNear: 80, fogFar: 250 },
  ultra: { dpr: 2, shadows: true, shadowSize: 2048, trees: 260, grass: true, fogNear: 100, fogFar: 320 },
};

/* ============================================================ state */
const state = {
  lang: "ru",
  gfx: "high",
  mode: "loading",
  returnTo: "menu",
  yaw: 0,
  pitch: -0.08,
  third: true,
  onGround: true,
  vy: 0,
  player: new THREE.Vector3(2, 0, 10),
  keys: {},
  signNear: null,
};

function saveSettings() {
  try { localStorage.setItem("walker.settings", JSON.stringify({ lang: state.lang, gfx: state.gfx })); } catch (e) {}
}
function loadSettings() {
  try {
    const s = JSON.parse(localStorage.getItem("walker.settings") || "{}");
    if (s.lang === "ru" || s.lang === "en") state.lang = s.lang;
    if (PRESETS[s.gfx]) state.gfx = s.gfx;
  } catch (e) {}
}
loadSettings();

/* ============================================================ terrain math */
const WATER = -1.35;
const WORLD = 380;

function hash(x, y) {
  const h = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return h - Math.floor(h);
}
function smooth(a, b, t) {
  t = Math.min(1, Math.max(0, (t - a) / (b - a)));
  return t * t * (3 - 2 * t);
}
function gauss(d, r) { return Math.exp(-(d * d) / (r * r)); }

function distToSegment(px, pz, ax, az, bx, bz) {
  const dx = bx - ax, dz = bz - az;
  const len2 = dx * dx + dz * dz;
  let t = len2 > 0 ? ((px - ax) * dx + (pz - az) * dz) / len2 : 0;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (ax + dx * t), pz - (az + dz * t));
}
const RIVER = [[88, 14], [46, -6], [6, -34], [-30, -62], [-58, -92]];
function riverDist(px, pz) {
  let d = 1e9;
  for (let i = 0; i < RIVER.length - 1; i++) {
    d = Math.min(d, distToSegment(px, pz, RIVER[i][0], RIVER[i][1], RIVER[i + 1][0], RIVER[i + 1][1]));
  }
  return d;
}

function heightAt(x, z) {
  let h = 1.1 * Math.sin(x * 0.05) * Math.cos(z * 0.042)
        + 0.7 * Math.sin(x * 0.11 + 1.7) * Math.sin(z * 0.093 + 0.4)
        + 0.3 * Math.sin(x * 0.23 + z * 0.19);
  h += Math.pow(smooth(62, 155, z), 1.6) * (24 + 15 * hash(Math.floor(x * 0.05), 7));
  h += Math.pow(smooth(72, 165, x), 1.6) * (20 + 13 * hash(3, Math.floor(z * 0.05)));
  h += Math.pow(smooth(-95, -185, x), 1.5) * 13;
  h += Math.pow(smooth(-105, -185, z), 1.5) * 11;
  // village plateau
  h *= 1 - 0.82 * gauss(Math.hypot(x - 0, z + 22), 42);
  h += 0.25 * gauss(Math.hypot(x - 0, z + 22), 42);
  // lake basin
  h -= 9.5 * gauss(Math.hypot(x + 58, z + 92), 36);
  // river channel
  h -= 3.4 * gauss(riverDist(x, z), 6.5);
  // waterfall pool + cliff
  h -= 4.5 * gauss(Math.hypot(x - 87, z - 14), 9);
  h += 13 * smooth(82, 95, x) * gauss(z - 14, 13);
  return h;
}
function slopeAt(x, z) {
  const e = 0.6;
  const dx = heightAt(x + e, z) - heightAt(x - e, z);
  const dz = heightAt(x, z + e) - heightAt(x, z - e);
  return Math.hypot(dx, dz) / (2 * e);
}

/* ============================================================ renderer */
const canvas = document.getElementById("c");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(62, innerWidth / innerHeight, 0.1, 600);
camera.rotation.order = "YXZ";

const hemi = new THREE.HemisphereLight(0xbdd6f0, 0x5a5243, 0.75);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xffd9a0, 2.3);
sun.position.set(60, 90, -40);
scene.add(sun);
scene.add(sun.target);
const dynamicLights = [];

let worldGroup = new THREE.Group();
scene.add(worldGroup);
const colliders = []; // {x, z, r}
const signs = []; // {x, z, key, mesh}

/* ============================================================ canvas textures */
function canvasTexture(w, h, draw, srgb = true) {
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
let terrainMap = null;
function terrainDetail() {
  if (terrainMap) return terrainMap;
  const c = document.createElement("canvas");
  c.width = 256; c.height = 256;
  const ctx = c.getContext("2d");
  const img = ctx.createImageData(256, 256);
  for (let y = 0; y < 256; y++) {
    for (let x = 0; x < 256; x++) {
      const n = 165 + (hash(x, y) - 0.5) * 60 + (hash(x >> 3, y >> 3) - 0.5) * 45;
      const i = (y * 256 + x) * 4;
      img.data[i] = n; img.data[i + 1] = n; img.data[i + 2] = n; img.data[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  terrainMap = new THREE.CanvasTexture(c);
  terrainMap.wrapS = THREE.RepeatWrapping;
  terrainMap.wrapT = THREE.RepeatWrapping;
  terrainMap.repeat.set(70, 70);
  terrainMap.anisotropy = 4;
  return terrainMap;
}
const waterMap = canvasTexture(128, 128, (ctx, w, h) => {
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 260; i++) {
    const v = 215 + Math.floor(hash(i, 3) * 40);
    ctx.fillStyle = `rgb(${v},${v},255)`;
    ctx.fillRect(hash(i, 1) * w, hash(i, 2) * h, 2 + hash(i, 4) * 10, 1.5);
  }
});
waterMap.wrapS = waterMap.wrapT = THREE.RepeatWrapping;
waterMap.repeat.set(24, 24);
const fallMap = canvasTexture(64, 256, (ctx, w, h) => {
  ctx.clearRect(0, 0, w, h);
  for (let i = 0; i < 40; i++) {
    const x = hash(i, 9) * w;
    ctx.fillStyle = `rgba(255,255,255,${0.25 + hash(i, 5) * 0.5})`;
    ctx.fillRect(x, 0, 1 + hash(i, 6) * 2.5, h);
  }
});
fallMap.wrapS = THREE.RepeatWrapping;
fallMap.wrapT = THREE.RepeatWrapping;

/* ============================================================ sky & fog */
function makeSky() {
  const tex = canvasTexture(16, 256, (ctx) => {
    const g = ctx.createLinearGradient(0, 0, 0, 256);
    g.addColorStop(0, "#5d8fc4");
    g.addColorStop(0.5, "#a8c3dc");
    g.addColorStop(0.78, "#e8cf9f");
    g.addColorStop(1, "#d9b98a");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 16, 256);
  });
  const sky = new THREE.Mesh(
    new THREE.SphereGeometry(480, 24, 16),
    new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide, fog: false, depthWrite: false })
  );
  scene.add(sky);
}
function applyFog() {
  const p = PRESETS[state.gfx];
  scene.fog = new THREE.Fog(0xd9c9a6, p.fogNear, p.fogFar);
}

/* ============================================================ terrain */
function terrainColor(h, s, x, z) {
  const c = new THREE.Color();
  if (h < WATER + 0.35) c.setRGB(0.46, 0.42, 0.32);
  else if (h < 2.2) c.setRGB(0.3, 0.42, 0.2).lerp(new THREE.Color(0.42, 0.5, 0.24), hash(x * 3, z * 3));
  else if (h < 9) c.setRGB(0.28, 0.38, 0.2).lerp(new THREE.Color(0.36, 0.4, 0.24), hash(x, z));
  else if (h < 18) c.setRGB(0.42, 0.4, 0.34).lerp(new THREE.Color(0.52, 0.5, 0.46), s * 0.6);
  else c.setRGB(0.75, 0.77, 0.8).lerp(new THREE.Color(0.93, 0.94, 0.96), smooth(18, 30, h));
  if (s > 0.75 && h > 3) c.lerp(new THREE.Color(0.45, 0.42, 0.38), Math.min(1, (s - 0.75) * 1.2));
  return c;
}
function makeTerrain() {
  const seg = 170;
  const geo = new THREE.PlaneGeometry(WORLD, WORLD, seg, seg);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  const colors = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), z = pos.getZ(i);
    const h = heightAt(x, z);
    pos.setY(i, h);
    const c = terrainColor(h, slopeAt(x, z), x, z);
    colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
  }
  geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geo.computeVertexNormals();
  const mat = new THREE.MeshStandardMaterial({
    vertexColors: true, roughness: 0.92, metalness: 0, map: terrainDetail(),
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.receiveShadow = true;
  worldGroup.add(mesh);
}

/* ============================================================ water */
let water = null;
function makeWater() {
  const geo = new THREE.PlaneGeometry(WORLD * 1.2, WORLD * 1.2, 1, 1);
  geo.rotateX(-Math.PI / 2);
  const mat = new THREE.MeshStandardMaterial({
    color: 0x2e5f6e, map: waterMap, transparent: true, opacity: 0.86,
    roughness: 0.25, metalness: 0.35,
  });
  water = new THREE.Mesh(geo, mat);
  water.position.y = WATER;
  worldGroup.add(water);
}

/* ============================================================ village */
function box(w, h, d, color, x, y, z) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshStandardMaterial({ color, roughness: 0.85 }));
  m.position.set(x, y, z);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}
const HOUSES = [
  { x: -8, z: -16, r: 0.3, w: 4.2, d: 3.4, c: 0xcfc3a8, roof: 0x8a4a32 },
  { x: 2, z: -26, r: -0.4, w: 4.8, d: 3.8, c: 0xd8ccb0, roof: 0x74402c },
  { x: 11, z: -18, r: 0.9, w: 3.8, d: 3.2, c: 0xc4b294, roof: 0x8f5a3a },
  { x: -14, z: -28, r: -1.1, w: 4.4, d: 3.6, c: 0xd2c0a0, roof: 0x6e3d2a },
  { x: 8, z: -34, r: 2.2, w: 4.0, d: 3.4, c: 0xcbb898, roof: 0x84482f },
  { x: -2, z: -8, r: 1.7, w: 3.6, d: 3.0, c: 0xdccfb4, roof: 0x7c4630 },
];
function makeVillage() {
  for (const H of HOUSES) {
    const g = new THREE.Group();
    const gh = heightAt(H.x, H.z);
    g.position.set(H.x, gh, H.z);
    g.rotation.y = H.r;
    const bodyH = 2.3;
    g.add(box(H.w, bodyH, H.d, H.c, 0, bodyH / 2, 0));
    const roof = new THREE.Mesh(
      new THREE.ConeGeometry(Math.max(H.w, H.d) * 0.82, 1.7, 4),
      new THREE.MeshStandardMaterial({ color: H.roof, roughness: 0.8 })
    );
    roof.position.y = bodyH + 0.85;
    roof.rotation.y = Math.PI / 4;
    roof.castShadow = true;
    g.add(roof);
    g.add(box(0.9, 1.5, 0.12, 0x4a3320, 0, 0.75, H.d / 2 + 0.02));
    const winMat = new THREE.MeshStandardMaterial({ color: 0xffca6a, emissive: 0xff9d3a, emissiveIntensity: 0.55, roughness: 0.4 });
    g.add(new THREE.Mesh(new THREE.PlaneGeometry(0.55, 0.55), winMat)).position.set(H.w / 3, 1.45, H.d / 2 + 0.02);
    g.add(box(0.45, 1.1, 0.45, 0x776a58, -H.w / 4, bodyH + 0.9, -H.d / 5));
    worldGroup.add(g);
    colliders.push({ x: H.x, z: H.z, r: Math.max(H.w, H.d) * 0.72 });
  }
  // well
  const well = new THREE.Group();
  const wy = heightAt(1, -19);
  well.position.set(1, wy, -19);
  const ring = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 1, 0.9, 12, 1, true), new THREE.MeshStandardMaterial({ color: 0x8d857a, roughness: 0.95 }));
  ring.position.y = 0.45;
  ring.castShadow = true;
  well.add(ring);
  well.add(box(0.12, 1.7, 0.12, 0x6a4a2e, -0.85, 0.85, 0));
  well.add(box(0.12, 1.7, 0.12, 0x6a4a2e, 0.85, 0.85, 0));
  const wroof = new THREE.Mesh(new THREE.ConeGeometry(1.35, 0.7, 4), new THREE.MeshStandardMaterial({ color: 0x74402c, roughness: 0.8 }));
  wroof.position.y = 2.0;
  wroof.rotation.y = Math.PI / 4;
  well.add(wroof);
  worldGroup.add(well);
  colliders.push({ x: 1, z: -19, r: 1.1 });
  // fences
  const fenceMat = new THREE.MeshStandardMaterial({ color: 0x7a5c3c, roughness: 0.9 });
  for (let i = 0; i < 26; i++) {
    const a = (i / 26) * Math.PI * 2;
    const x = Math.cos(a) * 17, z = -20 + Math.sin(a) * 14;
    if (hash(i, 11) < 0.25) continue;
    const post = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.9, 0.12), fenceMat);
    post.position.set(x, heightAt(x, z) + 0.45, z);
    post.castShadow = true;
    worldGroup.add(post);
  }
  const lampMat = new THREE.MeshStandardMaterial({ color: 0xffd27a, emissive: 0xffb347, emissiveIntensity: 1.4 });
  for (const [x, z] of [[-5, -12], [7, -24]]) {
    const pole = box(0.14, 2.6, 0.14, 0x3f3428, x, heightAt(x, z) + 1.3, z);
    worldGroup.add(pole);
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.16, 8, 6), lampMat);
    bulb.position.set(x, heightAt(x, z) + 2.65, z);
    worldGroup.add(bulb);
    const l = new THREE.PointLight(0xffb85c, 6, 16, 2);
    l.position.set(x, heightAt(x, z) + 2.5, z);
    scene.add(l);
    dynamicLights.push(l);
  }
}

/* ============================================================ forest */
let forestMeshes = [];
function makeForest() {
  for (const m of forestMeshes) {
    worldGroup.remove(m);
    m.geometry.dispose();
  }
  forestMeshes = [];
  const count = PRESETS[state.gfx].trees;
  const trunkGeo = new THREE.CylinderGeometry(0.13, 0.24, 2.4, 6);
  trunkGeo.translate(0, 1.2, 0);
  const cone1 = new THREE.ConeGeometry(1.25, 2.6, 7);
  cone1.translate(0, 3.2, 0);
  const cone2 = new THREE.ConeGeometry(0.9, 2.0, 7);
  cone2.translate(0, 4.6, 0);
  const trunkMat = new THREE.MeshStandardMaterial({ color: 0x6a4a30, roughness: 0.95 });
  const leafMat = new THREE.MeshStandardMaterial({ color: 0x2d4a28, roughness: 0.9 });
  const leafMat2 = new THREE.MeshStandardMaterial({ color: 0x39602f, roughness: 0.9 });
  const trunks = new THREE.InstancedMesh(trunkGeo, trunkMat, count);
  const tops = new THREE.InstancedMesh(cone1, leafMat, count);
  const tops2 = new THREE.InstancedMesh(cone2, leafMat2, count);
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), S = new THREE.Vector3(), P = new THREE.Vector3();
  const placed = [];
  let rng = 1234;
  const rand = () => { rng = (rng * 16807) % 2147483647; return rng / 2147483647; };
  let i = 0, guard = 0;
  while (i < count && guard++ < count * 12) {
    const x = -100 + rand() * 82;
    const z = -78 + rand() * 116;
    const h = heightAt(x, z);
    if (h < 0.4 || h > 15 || slopeAt(x, z) > 0.9) continue;
    if (Math.hypot(x, z + 22) < 24) continue;
    if (riverDist(x, z) < 7) continue;
    let ok = true;
    for (const p of placed) if ((p.x - x) * (p.x - x) + (p.z - z) * (p.z - z) < 14) { ok = false; break; }
    if (!ok) continue;
    const s = 0.75 + rand() * 0.85;
    P.set(x, h - 0.1, z);
    Q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), rand() * 6.28);
    S.set(s, s * (0.9 + rand() * 0.35), s);
    M.compose(P, Q, S);
    trunks.setMatrixAt(i, M);
    tops.setMatrixAt(i, M);
    tops2.setMatrixAt(i, M);
    placed.push({ x, z, r: 0.5 * s });
    i++;
  }
  trunks.count = tops.count = tops2.count = i;
  trunks.castShadow = tops.castShadow = tops2.castShadow = true;
  worldGroup.add(trunks, tops, tops2);
  forestMeshes = [trunks, tops, tops2];
  for (const t of placed) colliders.push({ x: t.x, z: t.z, r: t.r + 0.25, tree: true });
}

/* ============================================================ waterfall */
let fallSheets = [];
let mist = null;
function makeFalls() {
  const topY = heightAt(97, 14);
  const baseY = heightAt(87, 14);
  const sheetGeo = new THREE.PlaneGeometry(7, topY - baseY + 1, 1, 1);
  const sheetMat = new THREE.MeshBasicMaterial({ map: fallMap, transparent: true, opacity: 0.75, depthWrite: false, side: THREE.DoubleSide });
  for (const off of [0, 0.35]) {
    const sheet = new THREE.Mesh(sheetGeo, sheetMat.clone());
    sheet.position.set(90 - off, (topY + baseY) / 2, 14);
    sheet.rotation.y = -Math.PI / 2;
    sheet.userData.falls = true;
    sheet.userData.baseX = sheet.position.x;
    worldGroup.add(sheet);
    fallSheets.push(sheet);
  }
  const crest = box(2.4, 0.5, 7, 0x6d675f, 95.5, topY + 0.1, 14);
  worldGroup.add(crest);
  const n = 220;
  const pts = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    pts[i * 3] = 88.5 + (hash(i, 1) - 0.5) * 3;
    pts[i * 3 + 1] = baseY + hash(i, 2) * (topY - baseY);
    pts[i * 3 + 2] = 14 + (hash(i, 3) - 0.5) * 7;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pts, 3));
  mist = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xeaf4f8, size: 0.55, transparent: true, opacity: 0.5, depthWrite: false }));
  mist.userData.baseY = baseY;
  mist.userData.span = topY - baseY;
  worldGroup.add(mist);
}

/* ============================================================ props */
function makeProps() {
  // bridge over the river bend
  const bridge = new THREE.Group();
  bridge.position.set(40, heightAt(40, -12) + 0.25, -12);
  bridge.rotation.y = 0.7;
  bridge.add(box(1.7, 0.14, 8.2, 0x8d6a45, 0, 0.55, 0));
  bridge.add(box(0.1, 0.7, 8.2, 0x6a4a2e, -0.8, 0.95, 0));
  bridge.add(box(0.1, 0.7, 8.2, 0x6a4a2e, 0.8, 0.95, 0));
  worldGroup.add(bridge);
  // dock on the lake
  const dock = new THREE.Group();
  dock.position.set(-46, Math.max(WATER + 0.12, heightAt(-46, -72)), -72);
  dock.rotation.y = 0.5;
  dock.add(box(1.5, 0.12, 6.4, 0x9a734c, 0, 0.25, 0));
  dock.add(box(0.12, 1.4, 0.12, 0x6b4a2c, -0.6, -0.35, -2.8));
  dock.add(box(0.12, 1.4, 0.12, 0x6b4a2c, 0.6, -0.35, -2.8));
  worldGroup.add(dock);
  // campfire near the village
  const fx = -16, fz = -8, fy = heightAt(fx, fz);
  worldGroup.add(box(0.95, 0.16, 0.95, 0x3e3832, fx, fy + 0.08, fz));
  const logs = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.75, 5), new THREE.MeshStandardMaterial({ color: 0x6a4a2c }));
  logs.position.set(fx, fy + 0.24, fz);
  logs.rotation.set(0, 0.4, Math.PI / 2);
  worldGroup.add(logs);
  const flame = new THREE.Mesh(new THREE.ConeGeometry(0.17, 0.55, 6), new THREE.MeshBasicMaterial({ color: 0xffb15a }));
  flame.position.set(fx, fy + 0.44, fz);
  flame.userData.baseY = flame.position.y;
  flame.name = "flame";
  worldGroup.add(flame);
  const fire = new THREE.PointLight(0xff7a3a, 8, 15, 2);
  fire.position.set(fx, fy + 0.8, fz);
  fire.userData.fire = true;
  scene.add(fire);
  dynamicLights.push(fire);
  // boulders
  for (const [x, z, s] of [[-18, 108, 1.6], [28, 128, 2.2], [6, 152, 2.6], [48, 96, 1.3], [-40, 140, 1.8], [112, 40, 2.4]]) {
    const y = heightAt(x, z);
    const rock = new THREE.Mesh(
      new THREE.DodecahedronGeometry(s, 0),
      new THREE.MeshStandardMaterial({ color: y > 16 ? 0xd5dbe0 : 0x8a847c, roughness: 0.94 })
    );
    rock.position.set(x, y + s * 0.35, z);
    rock.rotation.set(0.2, s, 0.4);
    rock.castShadow = true;
    worldGroup.add(rock);
    colliders.push({ x, z, r: s * 0.85 });
  }
}

/* ============================================================ grass */
let grassMesh = null;
let grassOrigin = null;
function makeGrass() {
  if (grassMesh) {
    worldGroup.remove(grassMesh);
    grassMesh.geometry.dispose();
    grassMesh = null;
  }
  const n = 700;
  const blade = new THREE.PlaneGeometry(0.16, 0.5);
  blade.translate(0, 0.25, 0);
  const geo = new THREE.InstancedBufferGeometry().copy(blade);
  const mat = new THREE.MeshStandardMaterial({ color: 0x4a7a3a, roughness: 1, side: THREE.DoubleSide, alphaTest: 0.5 });
  grassMesh = new THREE.InstancedMesh(geo, mat, n);
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), S = new THREE.Vector3(), P = new THREE.Vector3();
  let placed = 0, guard = 0;
  while (placed < n && guard++ < n * 6) {
    const x = state.player.x + (hash(guard, 1) - 0.5) * 46;
    const z = state.player.z + (hash(guard, 2) - 0.5) * 46;
    const h = heightAt(x, z);
    if (h < 0.35 || h > 7 || slopeAt(x, z) > 0.55 || riverDist(x, z) < 6) continue;
    if (Math.hypot(x, z + 20) < 12) continue;
    const s = 0.7 + hash(guard, 3) * 0.9;
    P.set(x, h, z);
    Q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), hash(guard, 4) * 6.28);
    S.set(s, s, s);
    M.compose(P, Q, S);
    grassMesh.setMatrixAt(placed, M);
    placed++;
  }
  grassMesh.count = placed;
  grassMesh.instanceMatrix.needsUpdate = true;
  grassOrigin = { x: state.player.x, z: state.player.z };
  worldGroup.add(grassMesh);
}
function maybeGrass() {
  if (!PRESETS[state.gfx].grass) return;
  if (!grassOrigin || Math.hypot(state.player.x - grassOrigin.x, state.player.z - grassOrigin.z) > 16) makeGrass();
}

/* ============================================================ signs */
function signTexture(title) {
  return canvasTexture(512, 256, (ctx) => {
    ctx.fillStyle = "#7a5c3c";
    ctx.fillRect(0, 0, 512, 256);
    ctx.strokeStyle = "#4f3a24";
    ctx.lineWidth = 14;
    ctx.strokeRect(10, 10, 492, 236);
    ctx.fillStyle = "#f2e3c2";
    ctx.font = "bold 44px 'DejaVu Sans', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const words = title.split(" ");
    const lines = [];
    let line = "";
    for (const w of words) {
      if ((line + " " + w).trim().length > 18) { lines.push(line.trim()); line = w; } else line += " " + w;
    }
    lines.push(line.trim());
    lines.forEach((l, i) => ctx.fillText(l, 256, 128 + (i - (lines.length - 1) / 2) * 54));
  });
}
const SIGN_SPOTS = [
  { key: "village", x: 4, z: 2 },
  { key: "forest", x: -26, z: -12 },
  { key: "mountain", x: 30, z: 44 },
  { key: "falls", x: 74, z: 6 },
  { key: "lake", x: -38, z: -64 },
];
function makeSigns() {
  for (const s of signs) {
    worldGroup.remove(s.mesh);
    s.mesh.traverse((o) => { if (o.material && o.material.map) o.material.map.dispose(); if (o.material) o.material.dispose(); if (o.geometry) o.geometry.dispose(); });
  }
  signs.length = 0;
  const S = STR[state.lang];
  for (const spot of SIGN_SPOTS) {
    const g = new THREE.Group();
    const y = heightAt(spot.x, spot.z);
    g.position.set(spot.x, y, spot.z);
    g.rotation.y = Math.atan2(2 - spot.x, 8 - spot.z);
    const post = new THREE.Mesh(new THREE.BoxGeometry(0.14, 1.9, 0.14), new THREE.MeshStandardMaterial({ color: 0x5a432c, roughness: 0.95 }));
    post.position.y = 0.95;
    post.castShadow = true;
    g.add(post);
    const board = new THREE.Mesh(new THREE.PlaneGeometry(1.7, 0.85), new THREE.MeshStandardMaterial({ map: signTexture(S.signs[spot.key][0]), roughness: 0.8 }));
    board.position.y = 1.75;
    g.add(board);
    worldGroup.add(g);
    signs.push({ x: spot.x, z: spot.z, key: spot.key, mesh: g });
  }
}

/* ============================================================ player */
let soldier = null, mixer = null, actions = {};
function loadSoldier() {
  return new Promise((resolve, reject) => {
    new GLTFLoader().load("assets/Soldier.glb", (gltf) => {
      soldier = gltf.scene;
      soldier.traverse((o) => {
        if (o.isMesh) { o.castShadow = true; o.receiveShadow = false; o.frustumCulled = false; }
      });
      soldier.scale.setScalar(1.0);
      scene.add(soldier);
      mixer = new THREE.AnimationMixer(soldier);
      for (const clip of gltf.animations) {
        if (clip.name === "TPose") continue;
        actions[clip.name.toLowerCase()] = mixer.clipAction(clip);
      }
      actions.idle.play();
      resolve();
    }, undefined, reject);
  });
}
let curAction = "idle";
function setAction(name) {
  if (!actions[name] || name === curAction) return;
  const next = actions[name];
  const prev = actions[curAction];
  next.reset().play();
  if (prev) next.crossFadeFrom(prev, 0.25, false);
  curAction = name;
}

/* ============================================================ movement */
function collide(x, z) {
  // only "real" within ~5 m of the player, far objects stay visual
  for (const c of colliders) {
    const dx = x - c.x, dz = z - c.z;
    const d2 = dx * dx + dz * dz;
    const R = c.r + 0.4;
    if (d2 > R * R || d2 > 36) continue;
    const d = Math.sqrt(d2) || 0.001;
    if (d < R) {
      x = c.x + (dx / d) * R;
      z = c.z + (dz / d) * R;
    }
  }
  return [x, z];
}
function updatePlayer(dt) {
  const k = state.keys;
  let ix = (k.KeyD ? 1 : 0) - (k.KeyA ? 1 : 0);
  let iz = (k.KeyW ? 1 : 0) - (k.KeyS ? 1 : 0);
  const running = !!(k.ShiftLeft || k.ShiftRight) && iz > 0;
  const speed = running ? 6.2 : 3.3;
  const sin = Math.sin(state.yaw), cos = Math.cos(state.yaw);
  // camera looks along (-sin, -cos); W (iz=+1) must follow that
  let wx = ix * cos - iz * sin;
  let wz = -ix * sin - iz * cos;
  const len = Math.hypot(wx, wz);
  const moving = len > 0.01;
  if (moving) { wx /= len; wz /= len; }
  const p = state.player;
  if (moving) {
    let nx = p.x + wx * speed * dt;
    let nz = p.z + wz * speed * dt;
    const gh = heightAt(nx, nz);
    const maxStep = 3.4 * dt;
    if (gh - p.y > maxStep && p.y < gh + 0.2) {
      // try to slide along each axis
      const gx = heightAt(nx, p.z);
      const gz = heightAt(p.x, nz);
      if (gx - p.y <= maxStep) { nz = p.z; }
      else if (gz - p.y <= maxStep) { nx = p.x; }
      else { nx = p.x; nz = p.z; }
    }
    [nx, nz] = collide(nx, nz);
    p.x = Math.max(-WORLD / 2 + 2, Math.min(WORLD / 2 - 2, nx));
    p.z = Math.max(-WORLD / 2 + 2, Math.min(WORLD / 2 - 2, nz));
  }
  const ground = Math.max(heightAt(p.x, p.z), WATER + 0.15);
  state.vy -= 14.5 * dt;
  p.y += state.vy * dt;
  if (p.y <= ground) {
    p.y = ground;
    state.vy = 0;
    state.onGround = true;
  } else state.onGround = false;
  if (k.Space && state.onGround) {
    state.vy = 5.4;
    state.onGround = false;
  }
  // character
  if (soldier) {
    soldier.position.set(p.x, p.y, p.z);
    if (moving) {
      soldier.rotation.y = Math.atan2(-wx, -wz);
      state.yawMove = soldier.rotation.y;
    } else {
      // model natively faces -Z: rotation.y = yaw points it along the camera look dir
      soldier.rotation.y = state.yaw;
      state.yawMove = soldier.rotation.y;
    }
    setAction(moving ? (running ? "run" : "walk") : "idle");
    soldier.visible = state.third;
  }
  return { moving, running };
}
function updateCamera() {
  const p = state.player;
  if (!state.third) {
    camera.position.set(p.x, p.y + 1.55, p.z);
    camera.rotation.set(state.pitch, state.yaw, 0);
    return;
  }
  const cp = Math.cos(state.pitch), sp = Math.sin(state.pitch);
  const lx = -Math.sin(state.yaw) * cp;
  const ly = sp;
  const lz = -Math.cos(state.yaw) * cp;
  const dist = 3.6;
  let cx = p.x - lx * dist;
  let cy = p.y + 1.5 - ly * dist;
  let cz = p.z - lz * dist;
  cy = Math.max(cy, heightAt(cx, cz) + 0.35);
  camera.position.set(cx, cy, cz);
  camera.lookAt(p.x, p.y + 1.45, p.z);
}

/* ============================================================ hud */
function locationName() {
  const p = state.player;
  const S = STR[state.lang];
  const h = heightAt(p.x, p.z);
  if (Math.hypot(p.x - 87, p.z - 14) < 26) return S.loc.falls;
  if (Math.hypot(p.x + 58, p.z + 92) < 42) return S.loc.lake;
  if (Math.hypot(p.x, p.z + 22) < 24) return S.loc.village;
  if (p.x < -18 && p.x > -105 && p.z > -82 && p.z < 42) return S.loc.forest;
  if (h > 13) return S.loc.mountain;
  return S.loc.valley;
}
function updateHud() {
  const lx = -Math.sin(state.yaw), lz = -Math.cos(state.yaw);
  const ang = Math.atan2(lx, -lz);
  const idx = Math.round(((ang + Math.PI * 2) % (Math.PI * 2)) / (Math.PI / 4)) % 8;
  document.getElementById("compass").textContent = STR[state.lang].compass[idx];
  document.getElementById("loc").textContent = locationName();
  // nearest sign
  let best = null, bd = 3.5;
  for (const s of signs) {
    const d = Math.hypot(state.player.x - s.x, state.player.z - s.z);
    if (d < bd) { bd = d; best = s; }
  }
  state.signNear = best;
  const prompt = document.getElementById("prompt");
  prompt.style.display = best && state.mode === "play" ? "block" : "none";
  prompt.textContent = STR[state.lang].pressE;
  drawMap();
}
function drawMap() {
  const map = document.getElementById("map");
  if (!map.getContext) return;
  const ctx = map.getContext("2d");
  ctx.clearRect(0, 0, 150, 150);
  ctx.fillStyle = "rgba(22,30,24,0.5)";
  ctx.fillRect(0, 0, 150, 150);
  const toMap = (x, z) => [75 + x * 0.36, 75 + z * 0.36];
  ctx.fillStyle = "rgba(120,160,120,0.35)";
  const [fx, fz] = toMap(-60, -20);
  ctx.beginPath(); ctx.ellipse(fx, fz, 15, 20, 0.3, 0, 6.28); ctx.fill();
  ctx.fillStyle = "rgba(90,140,160,0.5)";
  const [lx2, lz2] = toMap(-58, -92);
  ctx.beginPath(); ctx.arc(lx2, lz2, 12, 0, 6.28); ctx.fill();
  ctx.fillStyle = "rgba(200,170,120,0.6)";
  const [vx, vz] = toMap(0, -22);
  ctx.fillRect(vx - 5, vz - 5, 10, 10);
  ctx.fillStyle = "rgba(230,240,250,0.8)";
  const [wx, wz] = toMap(88, 14);
  ctx.beginPath(); ctx.arc(wx, wz, 3.5, 0, 6.28); ctx.fill();
  // player
  const [px, pz] = toMap(state.player.x, state.player.z);
  ctx.fillStyle = "#e8c47a";
  ctx.beginPath(); ctx.arc(px, pz, 3.4, 0, 6.28); ctx.fill();
  ctx.strokeStyle = "#e8c47a";
  ctx.beginPath();
  ctx.moveTo(px, pz);
  ctx.lineTo(px - Math.sin(state.yaw) * 8, pz - Math.cos(state.yaw) * 8);
  ctx.stroke();
}

/* ============================================================ audio */
let audioCtx = null, ambGain = null, stepAt = 0;
function startAudio() {
  if (audioCtx) {
    if (audioCtx.state === "suspended") audioCtx.resume();
    return;
  }
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  try {
    audioCtx = new AC();
    const sec = 2;
    const buf = audioCtx.createBuffer(1, audioCtx.sampleRate * sec, audioCtx.sampleRate);
    const d = buf.getChannelData(0);
    let brown = 0;
    for (let i = 0; i < d.length; i++) {
      brown = brown * 0.98 + (Math.random() * 2 - 1) * 0.02;
      d[i] = brown * 3.2;
    }
    const src = audioCtx.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    const filter = audioCtx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 650;
    ambGain = audioCtx.createGain();
    ambGain.gain.value = 0.03;
    src.connect(filter); filter.connect(ambGain); ambGain.connect(audioCtx.destination);
    src.start();
  } catch (e) { audioCtx = null; }
}
function footstep() {
  if (!audioCtx) return;
  try {
    const osc = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    osc.type = "triangle";
    osc.frequency.value = 68 + Math.random() * 30;
    g.gain.setValueAtTime(0.07, audioCtx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.08);
    osc.connect(g); g.connect(audioCtx.destination);
    osc.start(); osc.stop(audioCtx.currentTime + 0.09);
  } catch (e) {}
}

/* ============================================================ UI flow */
function show(id) {
  for (const el of ["menu", "settings", "farewell", "read"]) {
    document.getElementById(el).classList.toggle("hidden", el !== id);
  }
  document.getElementById("hud").classList.toggle("hidden", id !== "hud");
}
function setMode(mode) {
  if (mode !== "play" && document.pointerLockElement === canvas && document.exitPointerLock) document.exitPointerLock();
  state.mode = mode;
  if (mode === "menu") show("menu");
  else if (mode === "settings") show("settings");
  else if (mode === "bye") show("farewell");
  else if (mode === "read") show("read");
  else if (mode === "play") show("hud");
  else if (mode === "pause") {
    show("menu");
  }
}
function applyLang() {
  const s = STR[state.lang];
  document.documentElement.lang = state.lang;
  document.getElementById("title").textContent = s.title;
  document.getElementById("subtitle").textContent = s.sub;
  document.getElementById("btnPlay").textContent = s.play;
  document.getElementById("btnSettings").textContent = s.settings;
  document.getElementById("btnQuit").textContent = s.quit;
  document.getElementById("settingsTitle").textContent = s.settingsTitle;
  document.getElementById("langLabel").textContent = s.lang;
  document.getElementById("gfxLabel").textContent = s.gfx;
  document.getElementById("btnSettingsBack").textContent = s.back;
  document.getElementById("byeTitle").textContent = s.byeTitle;
  document.getElementById("byeText").textContent = s.bye;
  document.getElementById("btnBack").textContent = s.resume;
  document.getElementById("btnReadClose").textContent = s.close;
  document.getElementById("hint").textContent = s.hint;
  document.getElementById("loadtext").textContent = s.loading;
  const lang = document.getElementById("lang");
  lang.innerHTML = `<option value="ru">Русский</option><option value="en">English</option>`;
  lang.value = state.lang;
  const gfx = document.getElementById("gfx");
  gfx.innerHTML = ["low", "medium", "high", "ultra"].map((k) => `<option value="${k}">${s.gfxNames[k]}</option>`).join("");
  gfx.value = state.gfx;
  document.title = s.title;
  if (state.mode !== "loading") makeSigns();
}
function applyGfx() {
  const p = PRESETS[state.gfx];
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, p.dpr));
  renderer.shadowMap.enabled = p.shadows;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  sun.castShadow = p.shadows;
  if (p.shadows) {
    sun.shadow.mapSize.set(p.shadowSize, p.shadowSize);
    if (sun.shadow.map) { sun.shadow.map.dispose(); sun.shadow.map = null; }
    const sc = sun.shadow.camera;
    sc.left = -48; sc.right = 48; sc.top = 48; sc.bottom = -48; sc.near = 10; sc.far = 260;
    sc.updateProjectionMatrix();
  }
  applyFog();
  makeForest();
  if (p.grass) makeGrass();
  else if (grassMesh) { worldGroup.remove(grassMesh); grassMesh.geometry.dispose(); grassMesh = null; }
}

/* ============================================================ input */
addEventListener("keydown", (e) => {
  state.keys[e.code] = true;
  if (e.code === "Space") e.preventDefault();
  if (e.code === "KeyV" && state.mode === "play") state.third = !state.third;
  if (e.code === "KeyE" && state.mode === "play" && state.signNear) openSign(state.signNear);
  if (e.code === "Escape") {
    if (state.mode === "pause") setMode("play");
    else if (state.mode === "read") setMode("play");
  }
});
addEventListener("keyup", (e) => { state.keys[e.code] = false; });

let dragging = false, lastX = 0, lastY = 0;
canvas.addEventListener("pointerdown", (e) => {
  dragging = true; lastX = e.clientX; lastY = e.clientY;
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener("pointerup", () => { dragging = false; });
canvas.addEventListener("pointermove", (e) => {
  if (state.mode !== "play") return;
  if (document.pointerLockElement === canvas) {
    state.yaw -= e.movementX * 0.0024;
    state.pitch = Math.max(-1.35, Math.min(1.2, state.pitch - e.movementY * 0.0024));
  } else if (dragging) {
    state.yaw -= (e.clientX - lastX) * 0.005;
    state.pitch = Math.max(-1.35, Math.min(1.2, state.pitch - (e.clientY - lastY) * 0.005));
    lastX = e.clientX; lastY = e.clientY;
  }
});
document.addEventListener("pointerlockchange", () => {
  if (document.pointerLockElement !== canvas && state.mode === "play") setMode("pause");
});

document.getElementById("btnPlay").onclick = () => {
  startAudio();
  setMode("play");
  if (canvas.requestPointerLock && matchMedia("(pointer: fine)").matches) canvas.requestPointerLock();
};
document.getElementById("btnSettings").onclick = () => {
  state.returnTo = state.mode === "pause" ? "pause" : "menu";
  setMode("settings");
};
document.getElementById("btnQuit").onclick = () => setMode("bye");
document.getElementById("btnSettingsBack").onclick = () => setMode(state.returnTo || "menu");
document.getElementById("btnBack").onclick = () => setMode("menu");
document.getElementById("btnReadClose").onclick = () => setMode("play");
document.getElementById("btnCam").onclick = () => { state.third = !state.third; };
document.getElementById("btnEsc").onclick = () => { if (state.mode === "play") setMode("pause"); };
document.getElementById("lang").onchange = (e) => { state.lang = e.target.value; saveSettings(); applyLang(); };
document.getElementById("gfx").onchange = (e) => { state.gfx = e.target.value; saveSettings(); applyGfx(); };

document.querySelectorAll("#pad button, #btnJump").forEach((b) => {
  const k = b.dataset.k || "Space";
  const on = (e) => { e.preventDefault(); state.keys[k] = true; };
  const off = (e) => { e.preventDefault(); state.keys[k] = false; };
  b.addEventListener("pointerdown", on);
  b.addEventListener("pointerup", off);
  b.addEventListener("pointerleave", off);
});

function openSign(s) {
  const S = STR[state.lang].signs[s.key];
  document.getElementById("readTitle").textContent = S[0];
  document.getElementById("readBody").textContent = S[1];
  setMode("read");
}

/* ============================================================ loop */
const clock = new THREE.Clock();
let mapTimer = 0;
function tick() {
  requestAnimationFrame(tick);
  const dt = Math.min(clock.getDelta(), 0.05);
  const t = clock.elapsedTime;
  if (mixer) mixer.update(dt);
  // animated world bits
  if (water) waterMap.offset.y = t * 0.03 % 1;
  for (const s of fallSheets) {
    if (s.material.map) s.material.map.offset.y = -t * 0.6 % 1;
    s.position.x = s.userData.baseX + Math.sin(t * 3) * 0.05;
  }
  if (mist) {
    const pos = mist.geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      let y = pos.getY(i) - dt * (3 + (i % 5) * 0.6);
      if (y < mist.userData.baseY) y = mist.userData.baseY + mist.userData.span;
      pos.setY(i, y);
    }
    pos.needsUpdate = true;
  }
  worldGroup.traverse((o) => {
    if (o.name === "flame") {
      o.scale.y = 0.75 + Math.sin(t * 14) * 0.28;
      o.position.y = o.userData.baseY + Math.sin(t * 9) * 0.035;
    }
  });
  for (const l of dynamicLights) {
    if (l.userData.fire) l.intensity = 6 + Math.sin(t * 13) * 2.4;
  }
  if (state.mode === "play") {
    const move = updatePlayer(dt);
    updateCamera();
    maybeGrass();
    mapTimer -= dt;
    if (mapTimer <= 0) { updateHud(); mapTimer = 0.2; }
    if (sun.castShadow) {
      sun.target.position.set(state.player.x, 0, state.player.z);
      sun.position.set(state.player.x + 60, 90, state.player.z - 40);
    }
    if (ambGain) {
      const fallD = Math.hypot(state.player.x - 88, state.player.z - 14);
      ambGain.gain.value = 0.025 + Math.max(0, 0.16 - fallD / 260);
    }
    if (move.moving && state.onGround) {
      stepAt -= dt;
      if (stepAt <= 0) { footstep(); stepAt = move.running ? 0.32 : 0.48; }
    }
  } else if (state.mode === "menu" || state.mode === "settings" || state.mode === "bye") {
    const a = t * 0.08;
    const x = Math.sin(a) * 26;
    const z = -30 + Math.cos(a) * 18;
    camera.position.set(x, heightAt(x, z) + 8, z);
    camera.lookAt(0, heightAt(0, -24) + 2, -24);
    if (soldier) {
      soldier.visible = true;
      soldier.position.set(2, heightAt(2, 4), 4);
      soldier.rotation.y = Math.PI * 0.9;
      setAction("idle");
    }
  }
  renderer.render(scene, camera);
}

/* ============================================================ boot */
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
async function boot() {
  const barQ = document.querySelector("#bar i");
  try { await document.fonts.load("16px 'DejaVu Sans'"); } catch (e) {}
  renderer.setSize(innerWidth, innerHeight);
  applyLang();
  makeSky();
  applyFog();
  barQ.style.width = "15%";
  makeTerrain();
  barQ.style.width = "40%";
  makeWater();
  makeVillage();
  barQ.style.width = "55%";
  makeForest();
  barQ.style.width = "70%";
  makeFalls();
  makeProps();
  makeSigns();
  barQ.style.width = "82%";
  applyGfx();
  state.player.y = Math.max(heightAt(state.player.x, state.player.z), WATER);
  try {
    await loadSoldier();
  } catch (e) {
    console.warn("soldier model failed", e);
  }
  barQ.style.width = "100%";
  document.getElementById("load").style.display = "none";
  setMode("menu");
  tick();
}
boot();
