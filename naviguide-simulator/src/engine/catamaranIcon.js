/** Vue de dessus : proue vers le haut (nord carte). `rotate(cap)` aligne la proue. */
export function catamaranTransform(bearing) {
  const deg = ((Number(bearing) || 0) % 360 + 360) % 360;
  return `rotate(${deg}deg)`;
}

function hullPath(cx) {
  const l = cx - 6.6;
  const r = cx + 6.6;
  return [
    `M ${cx} 4.2`,
    `C ${cx + 2.1} 4.6, ${r - 0.2} 9.5, ${r} 15`,
    `L ${r - 0.15} 49`,
    `C ${r} 53.2, ${cx + 3.8} 56.4, ${cx + 2.4} 58.2`,
    `L ${cx + 2.4} 59.4`,
    `L ${cx - 2.4} 59.4`,
    `L ${cx - 2.4} 58.2`,
    `C ${cx - 3.8} 56.4, ${l} 53.2, ${l + 0.15} 49`,
    `L ${l} 15`,
    `C ${l + 0.2} 9.5, ${cx - 2.1} 4.6, ${cx} 4.2`,
    "Z",
  ].join(" ");
}

/** Catamaran lisible à l’échelle carte : deux coques, trampoline, roof, mât. Proue = haut. */
export function catamaranSvg(bearing, { size = 64 } = {}) {
  const deg = ((Number(bearing) || 0) % 360 + 360) % 360;
  return `<svg class="marker-rotatable catamaran-icon-art" data-marker-rotatable xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 64 64" aria-label="catamaran" data-bow="north" data-heading="${deg}" style="display:block">
  <ellipse cx="32" cy="33" rx="21" ry="26" fill="#0a1a26"/>
  <path d="M23 11 L41 11 L42.2 21 L21.8 21 Z" fill="#2e4a5e"/>
  <path d="M24.2 12.2 L39.8 12.2 L40.4 19.6 L23.6 19.6 Z" fill="#1b3448"/>
  <path d="M25 13.4 L28 13.4 L28 18.6 L25.4 18.6 Z" fill="currentColor" opacity="0.35"/>
  <path d="M30 13.4 L34 13.4 L34 18.6 L30 18.6 Z" fill="currentColor" opacity="0.25"/>
  <path d="M36 13.4 L39 13.4 L38.6 18.6 L36 18.6 Z" fill="currentColor" opacity="0.35"/>
  <rect x="21.5" y="20.5" width="21" height="2.2" rx="1" fill="#9cb0ba"/>
  <rect x="22" y="22.4" width="20" height="22.2" rx="3.2" fill="#183246"/>
  <rect x="23.4" y="24" width="17.2" height="12.4" rx="2.2" fill="#1b3448" stroke="#9cb0ba" stroke-width="0.85"/>
  <rect x="25" y="26" width="5.4" height="5" rx="0.8" fill="#d3dee3" opacity="0.7"/>
  <rect x="33.6" y="26" width="5.4" height="5" rx="0.8" fill="#d3dee3" opacity="0.45"/>
  <rect x="25" y="32.2" width="14" height="2.6" rx="0.6" fill="#2e4a5e"/>
  <rect x="24.2" y="38.2" width="15.6" height="5.4" rx="1.2" fill="#2e4a5e"/>
  <rect x="21.5" y="44.6" width="21" height="2.2" rx="1" fill="#9cb0ba"/>
  <circle cx="32" cy="21.6" r="2.35" fill="#f2f6f8" stroke="#0a1a26" stroke-width="0.75"/>
  <line x1="32" y1="21.6" x2="32" y2="36.5" stroke="#e8eff2" stroke-width="1.05"/>
  <path d="${hullPath(19.2)}" fill="#f2f6f8" stroke="#0a1a26" stroke-width="1.2" stroke-linejoin="round"/>
  <path d="${hullPath(44.8)}" fill="#f2f6f8" stroke="#0a1a26" stroke-width="1.2" stroke-linejoin="round"/>
  <path d="M17.4 12.5 L20.8 12.5 L21.3 50.5 L16.9 50.5 Z" fill="#557080" opacity="0.7"/>
  <path d="M43.2 12.5 L46.6 12.5 L47.1 50.5 L42.7 50.5 Z" fill="#557080" opacity="0.7"/>
  <path d="M32 2.4 L37.2 11.2 L26.8 11.2 Z" fill="currentColor" stroke="#0a1a26" stroke-width="0.75" stroke-linejoin="round"/>
  <circle cx="32" cy="56.6" r="1.2" fill="#7e94a0"/>
</svg>`;
}
