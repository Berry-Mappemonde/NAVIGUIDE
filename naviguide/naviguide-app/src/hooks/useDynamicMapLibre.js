import { useEffect, useState } from "react";

/**
 * Charge react-map-gl / maplibre-gl uniquement quand `armed` est vrai (chunk séparé).
 */
export function useDynamicMapLibre(armed) {
  const [lib, setLib] = useState(null);

  useEffect(() => {
    if (!armed) return undefined;
    let cancelled = false;
    import("maplibre-gl/dist/maplibre-gl.css");
    import("react-map-gl/maplibre")
      .then((mod) => {
        if (cancelled) return;
        setLib({
          Map: mod.default,
          Source: mod.Source,
          Layer: mod.Layer,
          Marker: mod.Marker,
          Popup: mod.Popup,
        });
      })
      .catch((err) => console.warn("MapLibre load failed:", err));
    return () => {
      cancelled = true;
    };
  }, [armed]);

  return lib;
}
