import { atlasLayerUrl, atlasTileUrl } from "../utils/atlasPoint.js";

export async function fetchJson(url, signal) {
  const r = await fetch(url, { signal });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

/** True only when every tile failed with an error. Abort or any success → no fallback. */
export function allTilesErrored(outcomes) {
  if (!outcomes.length) return false;
  if (outcomes.some((o) => o === "abort")) return false;
  return outcomes.every((o) => o === "error");
}

export async function loadClimoLayerFeatures({
  kind,
  month,
  extra = {},
  tiles,
  cache,
  cacheKey,
  fetchJson: fetchFn = fetchJson,
  signal,
}) {
  const collections = [];
  const outcomes = [];
  const keyOf = cacheKey || ((tile) => `${kind}:${month}:${tile.z}/${tile.x}/${tile.y}`);

  await Promise.all((tiles || []).map(async (tile) => {
    const key = keyOf(tile);
    const hit = cache?.get(key);
    if (hit?.features) {
      outcomes.push("ok");
      collections.push(hit.features);
      return;
    }
    try {
      const data = await fetchFn(atlasTileUrl(kind, month, tile.z, tile.x, tile.y, extra), signal);
      const features = data?.features || [];
      cache?.set(key, { features });
      outcomes.push("ok");
      collections.push(features);
    } catch (err) {
      if (err?.name === "AbortError") {
        outcomes.push("abort");
        collections.push(null);
        return;
      }
      outcomes.push("error");
      collections.push([]);
    }
  }));

  if (signal?.aborted) {
    return { features: [], source: "tiles", aborted: true };
  }

  if (allTilesErrored(outcomes)) {
    try {
      const data = await fetchFn(
        atlasLayerUrl(kind, month, { ...extra, spacing_deg: "4" }),
        signal,
      );
      return { features: data?.features || [], source: "global", aborted: false };
    } catch (err) {
      if (err?.name === "AbortError") {
        return { features: [], source: "tiles", aborted: true };
      }
      return { features: [], source: null, aborted: false };
    }
  }

  return {
    features: collections.filter(Boolean).flat(),
    source: "tiles",
    aborted: false,
  };
}
