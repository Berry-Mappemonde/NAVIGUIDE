/**
 * Horloge « jours de mer » : le playhead reste en nm film, l’échelle
 * affichée peut passer en temps à une vitesse bateau (nœuds).
 * ~39 000 nm Berry à 7 kt ≈ 232 jours.
 */

import { FALLBACK_EXPEDITION_KNOTS } from "./playSpeeds.js";

export function boatKnotsOrCruise(knots) {
  const n = Number(knots);
  return Number.isFinite(n) && n > 0 ? n : FALLBACK_EXPEDITION_KNOTS;
}

/** Heures de mer pour une distance voile (nm), hors hops aériens. */
export function seaHours(sailNm, knots) {
  const nm = Number(sailNm);
  if (!Number.isFinite(nm) || nm <= 0) return 0;
  return nm / boatKnotsOrCruise(knots);
}

export function seaDays(sailNm, knots) {
  return seaHours(sailNm, knots) / 24;
}

/**
 * Libellé compact : « 4 h », « 2 j 6 h », « 232 j ».
 * @param {number} hours
 */
export function formatSeaTime(hours, { compact = false } = {}) {
  const h = Number(hours);
  if (!Number.isFinite(h) || h <= 0) return compact ? "0 h" : "0 h";
  if (h < 24) {
    const rounded = h < 10 ? Math.round(h * 10) / 10 : Math.round(h);
    return `${rounded} h`;
  }
  let days = Math.floor(h / 24);
  let rem = Math.round(h - days * 24);
  if (rem >= 24) {
    days += 1;
    rem = 0;
  }
  if (compact && days >= 10) return `${days} j`;
  if (rem <= 0) return `${days} j`;
  return `${days} j ${rem} h`;
}

export function formatSeaClock(sailNm, knots, opts) {
  return formatSeaTime(seaHours(sailNm, knots), opts);
}

/** Repères sous la barre : nm ou jours de mer (J0 … J232). */
export function clockTickLabels({ playheadTotal, sailTotalNm, knots, scale = "nm" } = {}) {
  const maxFilm = Number(playheadTotal) || 0;
  const sail = Math.max(0, Number(sailTotalNm) || 0);
  if (maxFilm <= 0) return [];
  const fractions = [0, 0.5, 1];
  if (scale === "days") {
    const totalH = seaHours(sail, knots);
    return fractions.map((t) => {
      const hours = totalH * t;
      const days = Math.round(hours / 24);
      return {
        filmNm: maxFilm * t,
        label: hours < 24 && t > 0 ? formatSeaTime(hours, { compact: true }) : `J${days}`,
      };
    });
  }
  return fractions.map((t) => ({
    filmNm: maxFilm * t,
    label: t === 0
      ? "0"
      : t === 1
        ? `${Math.round(sail).toLocaleString()} nm`
        : `${Math.round(sail * t).toLocaleString()}`,
  }));
}
