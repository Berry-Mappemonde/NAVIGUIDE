/** Cap dans le sens de la route, bateau toujours à l’endroit (pas de flip sud). */
export function catamaranTransform(bearing) {
  const deg = Number(bearing) || 0;
  const goingEast = Math.sin((deg * Math.PI) / 180) >= 0;
  const tilt = goingEast ? deg - 90 : deg - 270;
  const parts = [];
  if (!goingEast) parts.push("scaleX(-1)");
  parts.push(`rotate(${tilt}deg)`);
  return parts.join(" ");
}
