import { useCallback, useEffect, useRef, useState } from "react";
import { useEscaleSheet } from "./useEscaleSheet.js";
import { nearestAlongside, pickAutoEscaleStop } from "./escaleSheetPick.js";

export { nearestAlongside, pickAutoEscaleStop };

/**
 * Which stop's sheet is open (lot C, moved out of App.jsx in lot J): opened
 * from a flag click, and by itself in Suivre when the boat is alongside —
 * once per stop, the skipper may close it.
 * `clearToken` (RA5) : Suivre / Revoir vident la fiche et bloquent le
 * ré-auto-open immédiat. `filmActive` : pas de fiche pendant le film.
 * `userPickedRef` (RE2) : une fiche désignée n'est pas écrasée par l'auto-quai.
 */
export function useEscaleSheetState({
  lang, isSuivre, atQuay, clockSample, marks, onOpen, filmActive = false, clearToken = 0,
}) {
  const [stop, setStop] = useState(null);
  const sheet = useEscaleSheet(stop, lang);
  const autoRef = useRef(null);
  const holdRef = useRef(false);
  const userPickedRef = useRef(false);

  const open = useCallback((next) => {
    if (!next || !Number.isFinite(next.lat) || !Number.isFinite(next.lon)) return;
    holdRef.current = false;
    userPickedRef.current = true;
    autoRef.current = next.name;
    setStop({ name: next.name, lat: next.lat, lon: next.lon });
    onOpen?.();
  }, [onOpen]);

  const close = useCallback(() => {
    userPickedRef.current = false;
    if (stop) autoRef.current = stop.name;
    setStop(null);
  }, [stop]);

  useEffect(() => {
    if (!clearToken) return;
    holdRef.current = true;
    userPickedRef.current = false;
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
      userPickedRef.current = false;
      if (stop) setStop(null);
      return;
    }
    const best = pickAutoEscaleStop({
      filmActive,
      hold: holdRef.current,
      userPicked: userPickedRef.current,
      isSuivre,
      atQuay,
      clockSample,
      marks,
    });
    if (!best || autoRef.current === best.name) return;
    autoRef.current = best.name;
    setStop({ name: best.name, lat: best.lat, lon: best.lon });
  }, [filmActive, isSuivre, atQuay, clockSample, marks, stop]);

  return { stop, setStop, sheet, open, close };
}
