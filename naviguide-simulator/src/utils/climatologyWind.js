/**
 * Vent climatologique (zones). Copie autonome — pas d’import depuis naviguide/.
 * Ce n’est PAS une prévision. kind: climatology.
 */

function interp(v, v0, v1, r0, r1) {
  if (v1 === v0) return r0;
  const t = Math.max(0, Math.min(1, (v - v0) / (v1 - v0)));
  return r0 + t * (r1 - r0);
}

/**
 * @returns {{ speedKnots: number, dirFromDeg: number, source: string, kind: string }}
 */
export function zoneWindAt(lat, lon, month) {
  const m = Math.max(1, Math.min(12, Number(month) || 1));
  const pack = (speedKnots, dirFromDeg) => ({
    speedKnots,
    dirFromDeg,
    source: "zone_fallback",
    kind: "climatology",
  });
  if (lat > 60) return pack(18 + 4 * Math.sin((m * 30 * Math.PI) / 180), 240);
  if (lat < -60) return pack(28 + 5 * Math.sin((m * 30 * Math.PI) / 180), 270);

  const inAtlantic = lon >= -80 && lon <= 20;
  const inIndian = lon >= 20 && lon <= 120;
  const inPacific = lon >= 120 || lon <= -80;
  const inMed = lon >= -10 && lon <= 40 && lat >= 30 && lat <= 47;

  if (inMed) {
    if ([6, 7, 8].includes(m)) return pack(14, 340);
    if ([12, 1, 2].includes(m)) return pack(16, 220);
    return pack(10, 300);
  }
  if (inAtlantic && lat >= 25 && lat <= 40) {
    return [6, 7, 8, 9].includes(m) ? pack(10, 260) : pack(14, 240);
  }
  if (inAtlantic && lat >= 5 && lat <= 25) {
    let spd = 15;
    if ([12, 1, 2, 3].includes(m)) spd = 18;
    else if ([6, 7, 8, 9].includes(m)) spd = 12;
    return pack(spd, 50);
  }
  if (inAtlantic && lat >= -25 && lat <= 5) {
    return pack([6, 7, 8].includes(m) ? 16 : 13, 130);
  }
  if (inAtlantic && lat >= -50 && lat <= -25) {
    return pack(20 + 5 * interp(lat, -25, -50, 0, 1), 270);
  }
  if (inIndian && lat >= 5) {
    if ([6, 7, 8, 9].includes(m)) return pack(20, 225);
    if ([12, 1, 2, 3].includes(m)) return pack(14, 45);
    return pack(8, 90);
  }
  if (inIndian && lat >= -25 && lat <= 5) {
    return pack([6, 7, 8].includes(m) ? 17 : 13, 135);
  }
  if (inIndian && lat >= -60 && lat <= -25) {
    return pack(22 + 8 * interp(lat, -25, -60, 0, 1), 270);
  }
  if (inPacific && lat >= 5 && lat <= 25) {
    let spd = 14;
    if ([12, 1, 2, 3].includes(m)) spd = 17;
    else if ([7, 8, 9].includes(m)) spd = 12;
    return pack(spd, 55);
  }
  if (inPacific && lat >= -30 && lat <= 5) {
    return pack([6, 7, 8, 9].includes(m) ? 16 : 13, 120);
  }
  if (inPacific && lat >= 35 && lat <= 60) {
    return pack([12, 1, 2, 3].includes(m) ? 25 : 16, 260);
  }
  if (inPacific && lat >= -60 && lat <= -30) {
    return pack(20 + 7 * interp(lat, -30, -60, 0, 1), 270);
  }
  if (inAtlantic && lat >= 40 && lat <= 60) {
    return pack([12, 1, 2].includes(m) ? 22 : 15, 255);
  }
  if (Math.abs(lat) <= 8) {
    const itcz = 5 * Math.sin(((m - 7) * 30 * Math.PI) / 180);
    if (Math.abs(lat - itcz) < 4) return pack(4, 200);
  }
  if (lat >= -60 && lat <= -40) {
    return pack(25 + 5 * interp(lat, -40, -60, 0, 1), 275);
  }
  return pack(10, 270);
}

export function boatSpeedFromWind(windKnots) {
  const raw = Number(windKnots) * 0.45;
  return Math.round(Math.max(4, Math.min(11, raw)) * 10) / 10;
}

export function boatSpeedFromClimatology(lat, lon, month) {
  const wind = zoneWindAt(lat, lon, month);
  return {
    speedKnots: boatSpeedFromWind(wind.speedKnots),
    windKnots: Math.round(wind.speedKnots * 10) / 10,
    dirFromDeg: wind.dirFromDeg,
    source: wind.source,
    month,
    kind: "climatology",
  };
}
