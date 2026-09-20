import { useCallback, useEffect, useRef, useState } from "react";
import { haversineNm } from "../utils/geo.js";
import { useEscaleSheet } from "./useEscaleSheet.js";

const ALONGSIDE_NM = 5;

/**
 * Which stop's sheet is open (lot C, moved out of App.jsx in lot J): opened
 * from the Expedition list (▤) in any view, and by itself in Suivre when the
 * boat is alongside — once per stop, the skipper may close it.
 */
export function useEscaleSheetState({ lang, isSuivre, atQuay, clockSample, marks, onOpen }) {
  const [stop, setStop] = useState(null);
  const sheet = useEscaleSheet(stop, lang);
  const autoRef = useRef(null);

  const open = useCallback((next) => {
    if (!next || !Number.isFinite(next.lat) || !Number.isFinite(next.lon)) return;
    setStop({ name: next.name, lat: next.lat, lon: next.lon });
    onOpen?.();
  }, [onOpen]);

  const close = useCallback(() => {
    if (stop) autoRef.current = stop.name;
    setStop(null);
  }, [stop]);

  useEffect(() => {
    if (!isSuivre || !atQuay || !clockSample || !Number.isFinite(clockSample.lat)) return;
    let best = null;
    let bestD = Infinity;
    for (const m of marks || []) {
      if (!Number.isFinite(m.lat) || !Number.isFinite(m.lon)) continue;
      const d = haversineNm(clockSample.lat, clockSample.lon, m.lat, m.lon);
      if (d < bestD) { bestD = d; best = m; }
    }
    if (!best || bestD > ALONGSIDE_NM || autoRef.current === best.name) return;
    autoRef.current = best.name;
    setStop({ name: best.name, lat: best.lat, lon: best.lon });
  }, [isSuivre, atQuay, clockSample, marks]);

  return { stop, setStop, sheet, open, close };
}
