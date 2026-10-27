import { createElement } from "react";
import {
  Anchor,
  Compass,
  Dot,
  Fish,
  Flag,
  MapPin,
  MessageCircle,
  Microscope,
  Newspaper,
  NotebookPen,
  Stamp,
  TriangleAlert,
  Wind,
} from "lucide-react";

/**
 * Pictogrammes des types d'événements (journal de bord, bulle du film).
 * Les émojis de KIND_ICON (journalFormat.js) restent le symbole texte de
 * l'entrée ; à l'écran on dessine un trait lucide, à la couleur du texte,
 * à la taille du texte, caché aux lecteurs d'écran (le texte dit déjà tout).
 */
export const KIND_LUCIDE = Object.freeze({
  position: MapPin,
  stop: Anchor,
  grib: Wind,
  note: NotebookPen,
  zee: Flag,
  amp: Fish,
  poe: Stamp,
  wx: TriangleAlert,
  chat: MessageCircle,
  climo: Compass,
  sci: Microscope,
  news: Newspaper,
});

/** Type inconnu : un point, comme le « • » d'avant. */
export function kindIconComponent(kind) {
  // Own keys only: a kind such as "constructor" must not resolve to Object.
  return Object.hasOwn(KIND_LUCIDE, kind) ? KIND_LUCIDE[kind] : Dot;
}

export function KindIcon({ kind, className = "", strokeWidth = 2 }) {
  return createElement(kindIconComponent(kind), {
    size: "1em",
    strokeWidth,
    className,
    "aria-hidden": "true",
    focusable: "false",
    "data-kind-icon": kind || "?",
  });
}
