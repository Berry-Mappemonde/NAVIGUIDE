import { useMemo } from "react";

const ON = new Set(["1", "true", "yes", "on"]);

export function weatherPipelineEnabled(env) {
  const source = env ?? (typeof import.meta !== "undefined" ? import.meta.env : undefined);
  const raw = source?.VITE_NAVIGUIDE_WEATHER_PIPELINE ?? source?.NAVIGUIDE_WEATHER_PIPELINE ?? "";
  return ON.has(String(raw).trim().toLowerCase());
}

/** Per-layer state for the one wired provider (GRIB wind). Null when the flag is off. */
export function gribWindLayerState(grib, enabled) {
  if (!enabled) return null;
  const explicit = grib?.layers?.gribWind?.status;
  if (explicit === "pending" || explicit === "ready" || explicit === "unavailable") return explicit;
  if (!grib) return "pending";
  if (grib.status === "ready") return "ready";
  if (grib.status === "pending" || grib.refreshing) return "pending";
  return "unavailable";
}

/**
 * First render never waits on a provider: the state is derived, and blocksMap stays false.
 * With the flag off, layers.gribWind is null and the existing GRIB path is left alone.
 */
export function useWeatherPipeline({ grib, enabled } = {}) {
  const active = enabled ?? weatherPipelineEnabled();
  const gribWind = useMemo(() => gribWindLayerState(grib, active), [grib, active]);
  return {
    enabled: active,
    blocksMap: false,
    layers: { gribWind },
  };
}
