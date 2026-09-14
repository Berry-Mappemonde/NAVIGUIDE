import { useMemo } from "react";
import { buildVoyageClock, sampleClockAtFilmNm, sampleClockAtTime } from "../engine/voyageClock.js";

export function useVoyageClock({
  points,
  marks,
  t0,
  polarRaw,
  startAt = "la-rochelle",
  serverClock = null,
}) {
  const local = useMemo(() => {
    if (!points?.length || !t0) return null;
    return buildVoyageClock({ points, marks, t0, polarRaw, startAt });
  }, [points, marks, t0, polarRaw, startAt]);

  const clock = serverClock || local;
  return {
    clock,
    local,
    atFilmNm: (nm) => (clock ? sampleClockAtFilmNm(clock, nm) : null),
    atTime: (when) => (clock ? sampleClockAtTime(clock, when) : null),
  };
}
