import { useCallback, useMemo, useState } from "react";
import {
  DEFAULT_PORT_DAYS,
  DEFAULT_START_AT,
  DEFAULT_T0_ISO,
  simulationT0Iso,
  buildVoyageClock,
  lookupVoyageClock,
} from "../engine/voyageClock.js";

/**
 * Deux t0 : Suivre = 15 mai 2026 figé ; Simulation = aujourd’hui, éditable.
 */
export function useVoyageClock({
  flat,
  marks,
  polarRaw = null,
  enabled = true,
  stops = [],
  windAt = null,
  atlasRev = 0,
  mode = "simulation",
}) {
  const [simT0, setSimT0] = useState(() => simulationT0Iso());
  const [startAt, setStartAt] = useState(DEFAULT_START_AT);
  const t0 = mode === "suivre" ? DEFAULT_T0_ISO : simT0;

  const clock = useMemo(() => {
    if (!enabled || !flat?.points?.length) return null;
    return buildVoyageClock({
      flat,
      marks,
      t0,
      polarRaw,
      portDays: DEFAULT_PORT_DAYS,
      startAt,
      stops,
      windAt,
    });
  }, [enabled, flat, marks, t0, polarRaw, startAt, stops, windAt, atlasRev]);

  const sampleAt = useCallback(
    (filmNm, opts) => lookupVoyageClock(clock, filmNm, opts),
    [clock],
  );

  return { clock, t0, setT0: setSimT0, startAt, setStartAt, sampleAt };
}
