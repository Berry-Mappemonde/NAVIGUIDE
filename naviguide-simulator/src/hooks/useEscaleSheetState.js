import { useCallback, useEffect, useRef, useState } from "react";
import { haversineNm } from "../utils/geo.js";
import { useEscaleSheet } from "./useEscaleSheet.js";

const ALONGSIDE_NM = 5;

/**
 * Which stop's sheet is open (lot C, moved out of App.jsx in lot J): opened
 * from the Expedition list (▤) in any view, and by itself in Suivre when the
 * boat is alongside — once per stop, the skipper may close it.
 */
function nearestAlongside(clockSample, marks) {
  if (!clockSample || !Number.isFinite(clockSample.lat) || !Number.isFinite(clockSample.lon)) {
    return null;
  }
  let best = null;
  let bestD = Infinity;
  for (const m of marks || []) {
    if (!Number.isFinite(m.lat) || !Number.isFinite(m.lon)) continue;
    const d = haversineNm(clockSample.lat, clockSample.lon, m.lat, m.lon);
    if (d < bestD) { bestD = d; best = m; }
  }
  if (!best || bestD > ALONGSIDE_NM) return null;
  return best;
}

/**
 * Which stop's sheet is open (lot C, moved out of App.jsx in lot J): opened
 * from the Expedition list (▤) in any view, and by itself in Suivre when the
 * boat is alongside — once per stop, the skipper may close it.
 * `clearToken` (RA5) : Suivre / Revoir vident la fiche et bloquent le
 * ré-auto-open immédiat. `filmActive` : pas de fiche pendant le film.
 */
export function useEscaleSheetState({
  lang, isSuivre, atQuay, clockSample, marks, onOpen, filmActive = false, clearToken = 0,
}) {
  const [stop, setStop] = useState(null);
  const sheet = useEscaleSheet(stop, lang);
  const autoRef = useRef(null);
  const holdRef = useRef(false);

  const open = useCallback((next) => {
    if (!next || !Number.isFinite(next.lat) || !Number.isFinite(next.lon)) return;
    holdRef.current = false;
    autoRef.current = next.name;
    setStop({ name: next.name, lat: next.lat, lon: next.lon });
    onOpen?.();
  }, [onOpen]);

  const close = useCallback(() => {
    if (stop) autoRef.current = stop.name;
    setStop(null);
  }, [stop]);

  useEffect(() => {
    if (!clearToken) return;
    holdRef.current = true;
    if (stop) autoRef.current = stop.name;
    const near = nearestAlongside(clockSample, marks);
    if (near) autoRef.current = near.name;
    setStop(null);
    // clockSample / marks / stop : on fige l'escale courante au moment du nav.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clearToken]);

  useEffect(() => {
    if (!atQuay) holdRef.current = false;
  }, [atQuay]);

  useEffect(() => {
    if (filmActive) {
      holdRef.current = true;
      if (stop) setStop(null);
      return;
    }
    if (holdRef.current || !isSuivre || !atQuay) return;
    const best = nearestAlongside(clockSample, marks);
    if (!best || autoRef.current === best.name) return;
    autoRef.current = best.name;
    setStop({ name: best.name, lat: best.lat, lon: best.lon });
  }, [filmActive, isSuivre, atQuay, clockSample, marks, stop]);

  return { stop, setStop, sheet, open, close };
}
