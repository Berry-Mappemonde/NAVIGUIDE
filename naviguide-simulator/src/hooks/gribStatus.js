/** HUD GRIB : pas de message « absente » avant un fetch autour du bateau. */

export function officialGribStatus({ enabled, grib, pending, positioned } = {}) {
  if (!enabled) return null;
  if (grib?.status === "ready") return "ready";
  if (pending || !positioned || !grib) return "pending";
  return "absent";
}

export function officialGribWarning({ enabled, status } = {}) {
  if (!enabled || status !== "absent") return null;
  return "dernière prévision absente";
}
