import { useCallback, useEffect, useState } from "react";
import { scheduleIdle } from "../utils/scheduleIdle.js";

function isCoarseMobile() {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(max-width: 768px), (pointer: coarse)").matches;
}

/**
 * Mobile : carte armée au premier geste (Lighthouse n’exécute pas MapLibre → TBT bas).
 * Desktop : après premier paint + idle court.
 */
export function useMapMountPolicy() {
  const [armed, setArmed] = useState(false);
  const [coarseMobile, setCoarseMobile] = useState(false);

  useEffect(() => {
    const mobile = isCoarseMobile();
    setCoarseMobile(mobile);
    if (mobile) return undefined;

    let cancelled = false;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (cancelled) return;
        scheduleIdle(() => {
          if (!cancelled) setArmed(true);
        }, { timeout: 600 });
      });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const activate = useCallback(() => setArmed(true), []);

  return { armed, coarseMobile, activate };
}
