import { useEffect, useRef, useState } from "react";
import { expeditionBoatKnots, trueWindAngle } from "../engine/playSpeeds.js";

const API_URL = import.meta.env.VITE_API_URL ?? "";
const POLAR_API_URL = import.meta.env.VITE_POLAR_API_URL ?? import.meta.env.VITE_API_URL ?? "";

/**
 * Vitesse réelle du bateau : polaire de croisière, et en lecture « réelle »
 * raffinée par vent live × grille polaire si possible.
 */
export function useExpeditionSpeed({ polarData, sample, profile, playing, onLiveKnots }) {
  const cruise = expeditionBoatKnots(polarData);
  const [liveKnots, setLiveKnots] = useState(null);
  const sampleRef = useRef(sample);
  const onLiveRef = useRef(onLiveKnots);
  sampleRef.current = sample;
  onLiveRef.current = onLiveKnots;

  useEffect(() => {
    if (profile !== "real" || !playing || !polarData?.expedition_id) return undefined;
    let cancelled = false;
    const tick = async () => {
      const s = sampleRef.current;
      if (!s) return;
      try {
        const res = await fetch(`${API_URL}/wind`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ latitude: s.lat, longitude: s.lon }),
        });
        if (!res.ok) return;
        const wind = await res.json();
        const tws = Number(wind.wind_speed_knots);
        const twa = trueWindAngle(s.bearing, Number(wind.wind_direction));
        if (!Number.isFinite(tws) || twa == null) return;
        const spd = await fetch(
          `${POLAR_API_URL}/api/v1/polar/${encodeURIComponent(polarData.expedition_id)}/speed?twa=${twa}&tws=${tws}`,
        );
        if (!spd.ok) return;
        const body = await spd.json();
        const k = Number(body.speed);
        if (!cancelled && Number.isFinite(k) && k > 0) {
          setLiveKnots(k);
          onLiveRef.current?.(k);
        }
      } catch {
        /* on garde la croisière */
      }
    };
    tick();
    const id = setInterval(tick, 25000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [profile, playing, polarData?.expedition_id]);

  useEffect(() => {
    if (profile !== "real") {
      setLiveKnots(null);
      onLiveRef.current?.(null);
    }
  }, [profile]);

  const knots = liveKnots && liveKnots > 0 ? liveKnots : cruise;
  return { knots, cruise, live: Boolean(liveKnots) };
}
