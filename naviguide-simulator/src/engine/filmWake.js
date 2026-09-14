/**
 * Sillage du film : trait déjà parcouru, coupé aux sauts aériens
 * et à l’antiméridien. Code original NAVIGUIDE — idée type « trail »,
 * sans LeafletPlayback, TrackPlayBack ni deck.gl.
 */

import { splitAntimeridianCoords } from "../utils/geo.js";

/**
 * @returns {number[][][]} parties [lon, lat] jusqu’à sailNm
 */
export function wakeParts(flat, sailNm) {
  const pts = flat?.points || [];
  if (pts.length < 2) return [];
  const target = Math.max(0, Number(sailNm) || 0);
  const raw = [];
  let cur = [];

  const push = (lon, lat) => {
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
    cur.push([lon, lat]);
  };
  const flush = () => {
    if (cur.length >= 2) raw.push(cur);
    cur = [];
  };

  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    if ((p.cumNm ?? 0) > target + 1e-9) {
      const prev = i > 0 ? pts[i - 1] : null;
      if (prev && !p.jump && !prev.jump) {
        const span = ((p.cumNm ?? 0) - (prev.cumNm ?? 0)) || 1;
        const t = Math.max(0, Math.min(1, (target - (prev.cumNm ?? 0)) / span));
        if (t > 1e-6) {
          push(prev.lon + t * (p.lon - prev.lon), prev.lat + t * (p.lat - prev.lat));
        }
      }
      break;
    }
    if (p.jump) {
      flush();
      push(p.lon, p.lat);
      continue;
    }
    push(p.lon, p.lat);
  }
  flush();

  const parts = [];
  for (const coords of raw) {
    parts.push(...splitAntimeridianCoords(coords));
  }
  return parts;
}
