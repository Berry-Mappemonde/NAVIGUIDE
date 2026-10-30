/**
 * Barre de défilement du film au clavier (#103) : ←/→ = ±1 % de la barre, Maj = ±10 %,
 * Origine / Fin = début / bout. Rend la cible en milles (bornée), ou null si la touche ne la concerne pas.
 */
export function scrubKeyTarget(key, shiftKey, barNm, barTotal) {
  const total = Number(barTotal);
  if (!(total > 0)) return null;
  const at = Math.max(0, Math.min(total, Number(barNm) || 0));
  const step = total * (shiftKey ? 0.1 : 0.01);
  let target;
  switch (key) {
    case "ArrowLeft":
    case "ArrowDown":
      target = at - step;
      break;
    case "ArrowRight":
    case "ArrowUp":
      target = at + step;
      break;
    case "PageDown":
      target = at - total * 0.1;
      break;
    case "PageUp":
      target = at + total * 0.1;
      break;
    case "Home":
      target = 0;
      break;
    case "End":
      target = total;
      break;
    default:
      return null;
  }
  return Math.max(0, Math.min(total, target));
}

/**
 * Activation clavier d'un bouton (Entrée / Espace) : `click` sans pointeur, `detail === 0`.
 * La position viendrait alors de clientX = 0 (Chrome, Firefox) ou du centre (Safari) — on l'ignore.
 */
export function isKeyboardClick(e) {
  return Number(e?.detail) === 0;
}
