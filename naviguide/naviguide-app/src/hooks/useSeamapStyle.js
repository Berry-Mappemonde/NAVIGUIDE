import { useEffect, useState } from "react";
import { SEAMAP_STYLE_CANDIDATES, stripUnavailableSources } from "../utils/seamapStyle";
import { scheduleIdle } from "../utils/scheduleIdle.js";

const DEMO = "https://demotiles.maplibre.org/style.json";

export function useSeamapStyle() {
  const [mapStyle, setMapStyle] = useState(DEMO);

  useEffect(() => {
    let cancelled = false;
    const unique = [...new Set(SEAMAP_STYLE_CANDIDATES)];

    const cancelIdle = scheduleIdle(() => {
      (async () => {
        for (const url of unique) {
          if (cancelled) return;
          try {
            const res = await fetch(url);
            if (!res.ok) continue;
            const json = await res.json();
            if (!json?.sources && json?.version !== 8) continue;
            if (!cancelled) setMapStyle(stripUnavailableSources(json));
            return;
          } catch {
            /* essai suivant */
          }
        }
      })();
    }, { timeout: 6000 });

    return () => {
      cancelled = true;
      cancelIdle();
    };
  }, []);

  return mapStyle;
}
