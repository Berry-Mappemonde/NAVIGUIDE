import { worldCopyLngs } from "./gribSymbols.js";

/** Sources d’image : `flags` (1 ou 2) ou l’ancien champ unique `flag`. */
export function waypointFlagSrcs(point) {
  if (Array.isArray(point?.flags) && point.flags.length) {
    return point.flags.filter(Boolean);
  }
  if (point?.flag) return [point.flag];
  return [];
}

export function flagMarkerHtml(srcs, offset = [0, 0]) {
  const [ox, oy] = offset;
  if (!srcs.length) return "";
  const imgs = srcs
    .map((src) => `<img src="${src}" alt="" style="height:22px;width:auto;display:block" />`)
    .join("");
  return `<div class="flag-stack" style="display:flex;align-items:center;gap:2px;transform:translate(${ox}px,${oy}px)">${imgs}</div>`;
}

export function flagIconMetrics(srcs) {
  const n = Math.max(1, srcs.length);
  const w = 22 * n + 2 * Math.max(0, n - 1) + 4;
  return { iconSize: [w, 24], iconAnchor: [Math.round(w / 2), 12] };
}

/** Copie monde la plus proche du centre caméra (même wrap que la vue). */
export function lonOnCameraCopy(lon, cameraLng) {
  const copies = worldCopyLngs(lon);
  if (!copies.length) return Number(lon);
  const cam = Number(cameraLng);
  if (!Number.isFinite(cam)) return copies[0];
  return copies.reduce((best, x) => (Math.abs(x - cam) < Math.abs(best - cam) ? x : best));
}

export { worldCopyLngs };
