// Mesure de la cinématique du film (sans voix : horloge murale). Usage, depuis naviguide-simulator/ :
//   node scripts/film-cinematique.mjs http://localhost:5174/?view=suivre 45
// Relevé par requestAnimationFrame : frames, pas du bateau à l'écran, pan caméra, vitesse du temps-film (doc § 5.1).
// — frames, déplacement du bateau à l'écran par frame, pan caméra, vitesse du temps-film.
import { chromium } from "playwright";

const url = process.argv[2] || "http://localhost:5174/?view=suivre";
const seconds = Number(process.argv[3] || 45);
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 860 } });
page.on("pageerror", (e) => console.log("pageerror:", String(e).slice(0, 200)));
await page.goto(url, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__naviguideScene && window.__naviguideScene.map, null, { timeout: 60000 });
await page.waitForTimeout(6000);
const clicked = await page.evaluate(() => {
  const btn = [...document.querySelectorAll("button")].find((b) => /Revoir/.test(b.textContent || ""));
  if (!btn) return false;
  btn.click();
  return true;
});
if (!clicked) { console.log("pas de bouton Revoir"); await browser.close(); process.exit(1); }

const data = await page.evaluate((secs) => new Promise((resolve) => {
  const s = window.__naviguideScene;
  const map = s.map;
  const out = [];
  const t0 = performance.now();
  let prev = t0;
  const tick = (now) => {
    const f = window.__naviguideFilm || {};
    const boat = document.querySelector(".catamaran-divicon--live");
    let bx = null; let by = null;
    if (boat) { const r = boat.getBoundingClientRect(); bx = r.left + r.width / 2; by = r.top + r.height / 2; }
    const c = map.getCenter();
    out.push({
      t: now - t0, dt: now - prev,
      tMs: f.tMs ?? null, ch: f.chapterIdx ?? null, charIdx: f.charIdx ?? null,
      lat: f.lat ?? null, lon: f.lon ?? null,
      bx, by, cLat: c.lat, cLng: c.lng, zoom: map.getZoom(),
    });
    prev = now;
    if (now - t0 < secs * 1000) requestAnimationFrame(tick); else resolve(out);
  };
  requestAnimationFrame(tick);
}), seconds);

await page.screenshot({ path: "/tmp/film-cinematique.png" });
await browser.close();

// ---- statistiques
const frames = data.slice(1);
const dts = frames.map((r) => r.dt);
const q = (arr, p) => { const a = [...arr].sort((x, y) => x - y); return a[Math.min(a.length - 1, Math.floor(p * a.length))]; };
const long = dts.filter((d) => d > 34).length;
console.log(`frames: ${frames.length} sur ${seconds}s → ${(frames.length / seconds).toFixed(1)} fps ; dt médian ${q(dts, 0.5).toFixed(1)} ms, p95 ${q(dts, 0.95).toFixed(1)} ms, max ${Math.max(...dts).toFixed(0)} ms ; frames > 34 ms : ${long} (${(100 * long / frames.length).toFixed(1)} %)`);

// déplacement du bateau à l'écran par frame (hors changements de zoom)
const moves = [];
for (let i = 1; i < frames.length; i++) {
  const a = frames[i - 1]; const b = frames[i];
  if (a.bx == null || b.bx == null || a.zoom !== b.zoom) continue;
  moves.push(Math.hypot(b.bx - a.bx, b.by - a.by));
}
const zero = moves.filter((m) => m < 0.05).length;
console.log(`bateau à l'écran : ${moves.length} pas ; nuls (< 0,05 px) ${zero} (${(100 * zero / moves.length).toFixed(1)} %) ; médiane ${q(moves, 0.5).toFixed(2)} px, p90 ${q(moves, 0.9).toFixed(2)} px, p99 ${q(moves, 0.99).toFixed(2)} px, max ${Math.max(...moves).toFixed(1)} px`);

// pan caméra par frame (px) hors zoom
const pans = [];
for (let i = 1; i < frames.length; i++) {
  const a = frames[i - 1]; const b = frames[i];
  if (a.zoom !== b.zoom) continue;
  const scale = 256 * 2 ** b.zoom / 360;
  pans.push(Math.hypot((b.cLng - a.cLng) * scale, (b.cLat - a.cLat) * scale));
}
const pz = pans.filter((m) => m < 0.05).length;
console.log(`caméra : pas nuls ${pz} (${(100 * pz / pans.length).toFixed(1)} %) ; médiane ${q(pans, 0.5).toFixed(2)} px, p90 ${q(pans, 0.9).toFixed(2)} px, max ${Math.max(...pans).toFixed(1)} px ; changements de zoom : ${frames.filter((r, i) => i && r.zoom !== frames[i - 1].zoom).length}`);

// vitesse du temps-film (heures de film par seconde murale), par fenêtre de 1 s
const speeds = [];
for (let i = 60; i < frames.length; i += 60) {
  const a = frames[i - 60]; const b = frames[i];
  if (a.tMs == null || b.tMs == null || b.t === a.t) continue;
  speeds.push({ t: (b.t / 1000).toFixed(0), hPerS: ((b.tMs - a.tMs) / 3600000) / ((b.t - a.t) / 1000), ch: b.ch, charIdx: Math.round(b.charIdx) });
}
console.log("vitesse temps-film (h de voyage par seconde), par seconde :");
console.log(speeds.map((s) => `${s.t}s:ch${s.ch}@${s.charIdx}=${s.hPerS.toFixed(1)}h/s`).join("  "));
// sauts de temps-film entre deux frames
const jumps = [];
for (let i = 1; i < frames.length; i++) {
  const a = frames[i - 1]; const b = frames[i];
  if (a.tMs == null || b.tMs == null) continue;
  jumps.push((b.tMs - a.tMs) / 3600000);
}
console.log(`saut de temps-film par frame : médiane ${q(jumps, 0.5).toFixed(2)} h, p99 ${q(jumps, 0.99).toFixed(1)} h, max ${Math.max(...jumps).toFixed(1)} h ; frames sans avance ${jumps.filter((j) => j <= 0).length}`);
