import { useCallback, useMemo, useState } from "react";
import {
  DEFAULT_PORT_DAYS,
  DEFAULT_START_AT,
  DEFAULT_T0_ISO,
  buildVoyageClock,
  lookupVoyageClock,
} from "../engine/voyageClock.js";

/**
 * t0 + table d’horloge. Recalcul une fois si route, polar, t0 ou startAt changent.
 */
export function useVoyageClock({
  flat,
  marks,
  polarRaw = null,
  enabled = true,
  stops = [],
  windAt = null,
  atlasRev = 0,
}) {
  const [t0, setT0] = useState(DEFAULT_T0_ISO);
  const [startAt, setStartAt] = useState(DEFAULT_START_AT);

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

  return { clock, t0, setT0, startAt, setStartAt, sampleAt };
}
