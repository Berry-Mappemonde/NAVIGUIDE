import { useMemo } from "react";

const ON = new Set(["1", "true", "yes", "on"]);

export function weatherPipelineEnabled(env) {
  const source = env ?? (typeof import.meta !== "undefined" ? import.meta.env : undefined);
  const raw = source?.VITE_NAVIGUIDE_WEATHER_PIPELINE ?? source?.NAVIGUIDE_WEATHER_PIPELINE ?? "";
  return ON.has(String(raw).trim().toLowerCase());
}

/** Per-layer state for GRIB wind. Null when the flag is off. */
export function gribWindLayerState(grib, enabled) {
  if (!enabled) return null;
  const explicit = grib?.layers?.gribWind?.status;
  if (explicit === "pending" || explicit === "ready" || explicit === "unavailable") return explicit;
  if (!grib) return "pending";
  if (grib.status === "ready") return "ready";
  if (grib.status === "pending" || grib.refreshing) return "pending";
  return "unavailable";
}

/** Wave / current / other product body. Null when the flag is off — the old path stays. */
export function productLayerState(product, enabled) {
  if (!enabled) return null;
  if (!product) return "pending";
  const explicit = product.status;
  if (explicit === "pending" || explicit === "ready" || explicit === "unavailable") return explicit;
  if (explicit === "error" || explicit === "absent") return "unavailable";
  if (product.refreshing) return "pending";
  return "unavailable";
}

/** Atlas Blue Intelligence. Null when the flag is off. A cut atlas is unavailable, the map does not wait. */
export function climatologyLayerState(climo, enabled) {
  if (!enabled) return null;
  if (!climo) return "pending";
  if (climo.error) return "unavailable";
  if (climo.loading || climo.counts == null) return "pending";
  return "ready";
}

/**
 * First render never waits on a provider: the state is derived, and blocksMap stays false.
 * With the flag off, layer states are null and the existing paths are left alone.
 */
export function useWeatherPipeline({ grib, wave, current, climatology, enabled } = {}) {
  const active = enabled ?? weatherPipelineEnabled();
  const gribWind = useMemo(() => gribWindLayerState(grib, active), [grib, active]);
  const waveState = useMemo(() => productLayerState(wave, active), [wave, active]);
  const currentState = useMemo(() => productLayerState(current, active), [current, active]);
  const climatologyState = useMemo(
    () => climatologyLayerState(climatology, active),
    [climatology, active],
  );
  return {
    enabled: active,
    blocksMap: false,
    layers: { gribWind, wave: waveState, current: currentState, climatology: climatologyState },
  };
}
