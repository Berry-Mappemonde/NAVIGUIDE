import { memo, useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, ChevronLeft, ChevronRight, KeyRound, Loader2, Moon, Sun, TriangleAlert, Upload } from "lucide-react";
import { useLang } from "../i18n/LangContext.jsx";
import { adminHeaders, getAdminSecret, setAdminSecret } from "../utils/adminSecret.js";
import { SkipperOrdersPanel } from "./SkipperOrdersPanel.jsx";
import { EscaleLegend } from "./EscaleLegend.jsx";
import { PlanReview } from "./PlanReview.jsx";
import { DepartureField } from "./DepartureField.jsx";
import { LayerToggles, activeLayerCount } from "./LayerToggles.jsx";

const POLAR_API_URL = import.meta.env.VITE_POLAR_API_URL ?? "";
const POLAR_EXPEDITION = "berry-mappemonde-2026"; // pragma: allowlist secret
const POLAR_VMG_TWS_KEYS = ["8", "10", "12", "16", "20", "25"];

function kts(v) { return v != null ? `${Number(v).toFixed(1)} kt` : "—"; }
function deg(v) { return v != null ? `${Math.round(v)}°` : "—"; }

async function readPolarResponse(response) {
  let data = null;
  try {
    data = await response.json();
  } catch {
    // A proxy failure may have an HTML response rather than JSON.
  }
  if (response.ok) return data;

  const error = new Error(data?.detail ?? `HTTP ${response.status}`);
  error.status = response.status;
  error.detail = data?.detail;
  throw error;
}

function polarErrorDetail(error, t) {
  if (error?.code === "DEFAULT_POLAR_NOT_FOUND") return t("polarDefaultUnavailable");
  if (error?.status === 401 || error?.status === 503) return t("adminKeyRequired");
  if (error?.status === 413) return t("polarFileTooLarge");
  if (error?.status >= 500) {
    return t("polarServiceUnavailable", { status: error.status });
  }
  if (error?.detail) return error.detail;
  return t("polarNetworkError");
}

function PolarVmgRow({ tws, entry }) {
  const uw = entry?.upwind ?? {};
  const dw = entry?.downwind ?? {};
  return (
    <tr className="border-b border-slate-700/40 hover:bg-slate-800/40 transition-colors">
      <td className="py-1 pl-2 pr-1 text-center font-bold text-blue-300 text-xs w-8">{tws}</td>
      <td className="py-1 px-1 text-center text-xs text-green-300">{deg(uw.twa)}</td>
      <td className="py-1 px-1 text-center text-xs text-slate-200">{kts(uw.speed)}</td>
      <td className="py-1 px-1 text-center text-xs font-semibold text-green-400">{kts(uw.vmg)}</td>
      <td className="py-1 px-0.5 text-slate-600 text-center text-xs">│</td>
      <td className="py-1 px-1 text-center text-xs text-amber-300">{deg(dw.twa)}</td>
      <td className="py-1 px-1 text-center text-xs text-slate-200">{kts(dw.speed)}</td>
      <td className="py-1 pr-2 pl-1 text-center text-xs font-semibold text-amber-400">{kts(dw.vmg)}</td>
    </tr>
  );
}

/**
 * Sécurité P0 — la clé admin partagée (X-Naviguide-Admin), sur une ligne :
 * icône, champ « Coller la clé admin », OK. Stockée dans ce navigateur.
 */
function AdminKeyField() {
  const { t } = useLang();
  const [value, setValue] = useState(() => getAdminSecret());
  const [saved, setSaved] = useState(() => Boolean(getAdminSecret()));
  const commit = () => {
    setAdminSecret(value);
    setSaved(Boolean(value.trim()));
  };
  return (
    <div className="flex items-center gap-1.5" data-testid="admin-key">
      <KeyRound size={13} className={saved ? "text-emerald-400 flex-shrink-0" : "text-slate-500 flex-shrink-0"} title={saved ? t("adminKeyActive") : t("adminKeyLabel")} />
      <input
        type="password"
        autoComplete="off"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") commit(); }}
        placeholder={t("adminKeyPlaceholder")}
        aria-label={t("adminKeyLabel")}
        className="flex-1 min-w-0 bg-slate-900/70 border border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-200 placeholder:text-slate-500"
      />
      <button
        type="button"
        onClick={commit}
        className="px-2 py-1 rounded-lg text-xs font-semibold bg-slate-700 hover:bg-slate-600 text-slate-100"
      >
        {t("adminKeySave")}
      </button>
    </div>
  );
}

async function polarMetaFromUpload(data) {
  let raw = data.raw;
  if (!raw?.twa_rows && data.expedition_id) {
    try {
      const res = await fetch(`${POLAR_API_URL}/api/v1/polar/${encodeURIComponent(data.expedition_id)}`);
      if (res.ok) {
        const full = await res.json();
        raw = full.raw;
      }
    } catch {
      raw = null;
    }
  }
  return {
    expedition_id: data.expedition_id,
    boat_name: data.boat_name,
    grid_shape: data.grid_shape,
    vmg_summary: data.vmg_summary,
    created_at: data.created_at,
    raw: raw || null,
  };
}

function Toggle({ labelLeft, labelRight, active, onChange }) {
  const label = active ? labelRight : labelLeft;
  return (
    <button
      type="button"
      onClick={() => onChange(!active)}
      aria-label={label}
      aria-pressed={active}
      title={label}
      className={`w-10 h-5 rounded-full relative transition-colors ${active ? "bg-sky-500" : "bg-slate-600"}`}
    >
      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${active ? "left-5" : "left-0.5"}`} />
      <span className="sr-only">{label}</span>
      <span aria-hidden="true" className={`absolute top-1 ${active ? "left-1" : "right-1"} text-white/90`}>
        {active ? <Sun size={11} /> : <Moon size={11} />}
      </span>
    </button>
  );
}

function SectionTitle({ children, right = null }) {
  return (
    <div className="flex items-center justify-between gap-2 mb-1">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{children}</span>
      {right}
    </div>
  );
}

/**
 * The whole expedition, compact: the route in numbers on two lines and the
 * stopovers list (click = jump). Revue du 19 sept. : one box, not two.
 */
/** Lot I — while the skipper draws, the box describes the drawn route, not the official one. */
function DrawingBox({ drawing }) {
  const { t } = useLang();
  const pts = drawing?.points || [];
  return (
    <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/30 overflow-hidden" data-testid="drawing-box">
      <div className="px-3 py-1.5 text-[10px] text-slate-200 leading-snug flex flex-wrap gap-x-2 gap-y-0.5" data-testid="drawing-summary">
        <span className="font-semibold text-emerald-200">{t("drawingInProgress")}</span>
        <span>· {pts.length} {t("drawingPoints")}</span>
        <span>· {Number(drawing?.distanceNm || 0).toLocaleString()} nm</span>
        {drawing?.failed ? <span className="text-amber-300/90">· {drawing.failed} {t("drawingFailedSegments")}</span> : null}
      </div>
      {pts.length ? (
        <ol className="max-h-36 overflow-y-auto sidebar-scroll border-t border-white/5">
          {pts.map((p, i) => (
            <li key={`${p.lat}-${p.lon}-${i}`} className="px-2 py-1 text-[11px] text-white/80 border-t border-white/5 first:border-t-0 flex items-baseline gap-1">
              <span className="text-[9px] text-emerald-300/80 w-4 shrink-0">{i + 1}</span>
              <span className="truncate">{p.name}</span>
              <span className="ml-auto text-[9px] text-white/40 tabular-nums shrink-0">{p.lat.toFixed(2)}° · {p.lon.toFixed(2)}°</span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="px-3 pb-2 text-[10px] text-slate-400 leading-snug">{drawing?.message || t("drawStart")}</p>
      )}
    </div>
  );
}

function ExpeditionBox({ routeDistanceNm, routeSegmentCount, routeCounts, waypointCount, escaleMarks, filmNm, onSeekEscale, onEscaleSheet, drawing = null }) {
  const { t } = useLang();
  const nm = routeDistanceNm != null ? `${Number(routeDistanceNm).toLocaleString()} nm` : "—";
  if (drawing) return <DrawingBox drawing={drawing} />;
  return (
    <div className="rounded-xl border border-slate-700/40 bg-slate-800/40 overflow-hidden" data-testid="expedition-box">
      <div className="px-3 py-1.5 text-[10px] text-slate-300 leading-snug flex flex-wrap gap-x-2 gap-y-0.5" data-testid="route-summary">
        <span className="font-semibold text-white">{nm}</span>
        <span>· {routeSegmentCount ?? routeCounts.total} {t("routeSegmentsShort")}</span>
        <span>· {routeCounts.maritime} {t("routeSeaShort")} / {routeCounts.overland} {t("routeLandShort")}</span>
        <span>· {waypointCount} {t("waypoints").toLowerCase()}</span>
        <span>· {routeCounts.points.toLocaleString()} {t("routePointsShort")}</span>
      </div>
      <EscaleLegend marks={escaleMarks} filmNm={filmNm} onSeek={onSeekEscale} onSheet={onEscaleSheet} />
    </div>
  );
}

export const ToolsSidebar = memo(function ToolsSidebar({
  segments, points, open, onToggle,
  isLightMode, onLightModeChange,
  polarData, onPolarDataLoaded,
  routeDistanceNm, routeSegmentCount,
  maritimeLayers = null,
  escaleMarks = [], filmNm = 0, onSeekEscale, onEscaleSheet, drawing = null, planReview = null,
  showDeparture = false, departureT0, onDepartureT0,
  skipperOrders = null, skipperProfile = "cruise", onSkipperProfile, onSkipperReset,
  onSkipperComfort, onSkipperHorizon, onSkipperExpert, onSkipperBoat,
  skipperSuggest = null, onSkipperSuggestAccept, onSkipperSuggestDismiss,
}) {
  const { lang, switchLang, t } = useLang();
  const [polarFile, setPolarFile] = useState(null);
  const [polarUploadStatus, setPolarUploadStatus] = useState(null);
  const [polarUploadDetail, setPolarUploadDetail] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [showPolar, setShowPolar] = useState(false);
  const polarFileInputRef = useRef(null);
  const defaultLoadAttemptedRef = useRef(false);
  const userDroppedFileRef = useRef(false);

  useEffect(() => {
    if (polarFile) handlePolarUpload(polarFile);
  }, [polarFile]);

  useEffect(() => {
    if (polarData || defaultLoadAttemptedRef.current) return;
    defaultLoadAttemptedRef.current = true;
    const loadDefaultPolars = async () => {
      setPolarUploadStatus("uploading");
      try {
        const storedRes = await fetch(
          `${POLAR_API_URL}/api/v1/polar/${encodeURIComponent(POLAR_EXPEDITION)}/client`,
        );
        if (storedRes.ok) {
          const stored = await readPolarResponse(storedRes);
          if (userDroppedFileRef.current) return;
          onPolarDataLoaded(await polarMetaFromUpload(stored));
          setPolarUploadStatus("success");
          setPolarUploadDetail(stored.boat_name);
          return;
        }
        if (storedRes.status !== 404) {
          await readPolarResponse(storedRes);
        }
        const error = new Error("Default polar was not found.");
        error.code = "DEFAULT_POLAR_NOT_FOUND";
        throw error;
      } catch (err) {
        if (userDroppedFileRef.current) return;
        setPolarUploadStatus("error");
        setPolarUploadDetail(polarErrorDetail(err, t));
      }
    };
    loadDefaultPolars();
  }, [polarData, onPolarDataLoaded, t]);

  const handlePolarUpload = async (f) => {
    setPolarUploadStatus("uploading");
    setPolarUploadDetail("");
    const form = new FormData();
    form.append("file", f);
    form.append("expedition_id", POLAR_EXPEDITION);
    try {
      const res = await fetch(`${POLAR_API_URL}/api/v1/polar/upload`, {
        method: "POST",
        headers: adminHeaders(),
        body: form,
      });
      const data = await readPolarResponse(res);
      onPolarDataLoaded(await polarMetaFromUpload(data));
      setPolarUploadStatus("success");
      setPolarUploadDetail(data.boat_name);
    } catch (err) {
      setPolarUploadStatus("error");
      setPolarUploadDetail(polarErrorDetail(err, t));
    }
  };

  const routeCounts = useMemo(() => {
    const maritime = segments.filter((s) => !s.nonMaritime && s.coords?.length > 0);
    const overland = segments.filter((s) => s.nonMaritime && s.coords?.length > 0);
    return {
      maritime: maritime.length,
      overland: overland.length,
      total: maritime.length + overland.length,
      points: segments.reduce((count, segment) => count + (segment.coords?.length ?? 0), 0),
    };
  }, [segments]);

  const polarStatus = polarUploadStatus === "uploading"
    ? { icon: <Loader2 size={12} className="animate-spin" />, color: "text-blue-300", text: t("polarAnalyzing") }
    : polarUploadStatus === "error"
      ? { icon: <TriangleAlert size={12} />, color: "text-red-300", text: `${t("polarFailed")} — ${polarUploadDetail}` }
      : polarData
        ? { icon: <CheckCircle2 size={12} />, color: "text-emerald-300", text: `${t("polarLoaded")} — ${polarData.boat_name || polarUploadDetail || ""}` }
        : { icon: <Upload size={12} />, color: "text-slate-400", text: t("polarSection") };
  const layersOn = activeLayerCount(maritimeLayers);

  return (
    <>
      <button
        onClick={onToggle}
        className={`naviguide-sidebar-toggle naviguide-sidebar-toggle--right absolute top-4 z-30 bg-slate-900/95 text-white
          rounded-full w-9 h-9 flex items-center justify-center shadow-lg
          border border-slate-700
          hover:bg-slate-800 transition-all duration-300 ${open ? "right-[322px]" : "right-4"}`}
        title={open ? t("hideToolsPanel") : t("showToolsPanel")}
      >
        {open ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      <div
        className={`naviguide-sidebar-panel absolute top-0 right-0 h-full z-20 flex flex-col bg-slate-900/97
          border-l-2 border-sky-400/40 shadow-2xl transition-transform duration-300
          ${open ? "translate-x-0" : "translate-x-full"}`}
        style={{ width: 320 }}
      >
        <div className="flex-1 overflow-y-auto sidebar-scroll">
          <div className="px-4 py-3 border-b border-slate-700/60">
            <div className="flex items-center justify-between gap-3">
              <div className="flex bg-slate-800 rounded-full p-0.5 gap-0.5">
                <button type="button" onClick={() => switchLang("en")} aria-label={t("language")} title={t("language")} className={`px-3 py-1 rounded-full text-xs font-bold ${lang === "en" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"}`}>EN</button>
                <button type="button" onClick={() => switchLang("fr")} aria-label={t("language")} title={t("language")} className={`px-3 py-1 rounded-full text-xs font-bold ${lang === "fr" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"}`}>FR</button>
              </div>
              <Toggle labelLeft={t("dark")} labelRight={t("light")} active={isLightMode} onChange={onLightModeChange} />
            </div>
          </div>

          {/* ── L'expédition entière : la route en chiffres + les escales ── */}
          <div className="px-4 py-3 border-b border-slate-700/60">
            <SectionTitle>{t("expeditionTitle")}</SectionTitle>
            <ExpeditionBox
              routeDistanceNm={routeDistanceNm}
              routeSegmentCount={routeSegmentCount}
              routeCounts={routeCounts}
              waypointCount={points.length}
              escaleMarks={escaleMarks}
              filmNm={filmNm}
              onSeekEscale={onSeekEscale}
              onEscaleSheet={onEscaleSheet}
              drawing={drawing}
            />
            {planReview && !drawing ? (
              <div className="mt-2">
                <PlanReview legs={planReview.legs} loading={planReview.loading} error={planReview.error} summary={planReview.summary} />
              </div>
            ) : null}
            {showDeparture ? (
              <div className="mt-2">
                <DepartureField t0={departureT0} onT0={onDepartureT0} />
              </div>
            ) : null}
          </div>

          {/* ── Réglages : polaire compacte, clé admin, paramètres avancés, calques ── */}
          <div className="px-4 py-3 space-y-2">
            <div className="rounded-xl border border-slate-700/40 bg-slate-800/40 px-3 py-2" data-testid="polar-box">
              <div className={`flex items-center gap-2 text-xs ${polarStatus.color}`}>
                {polarStatus.icon}
                <span className="font-medium min-w-0 truncate">{polarStatus.text}</span>
                {polarData?.vmg_summary ? (
                  <button
                    type="button"
                    onClick={() => setShowPolar((v) => !v)}
                    aria-expanded={showPolar}
                    data-testid="polar-show"
                    className="ml-auto flex-shrink-0 px-2 py-0.5 rounded-md text-[10px] font-semibold border border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"
                  >
                    {showPolar ? t("polarHide") : t("polarShow")}
                  </button>
                ) : null}
              </div>
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault(); setIsDragging(false);
                  const f = e.dataTransfer.files?.[0];
                  const ok = [".pdf", ".csv", ".xlsx", ".xls"];
                  if (f && ok.some((ext) => f.name.toLowerCase().endsWith(ext))) {
                    userDroppedFileRef.current = true;
                    setPolarFile(f);
                  }
                }}
                onClick={() => polarFileInputRef.current?.click()}
                data-testid="polar-drop"
                className={`mt-1.5 flex items-center justify-center gap-1.5 px-2 py-1 border border-dashed rounded-lg cursor-pointer text-[10px]
                  ${isDragging ? "border-blue-400 bg-blue-900/20 text-blue-200" : "border-slate-600 hover:border-slate-500 text-slate-400"}`}
              >
                <input
                  ref={polarFileInputRef}
                  type="file"
                  accept=".pdf,.csv,.xlsx,.xls"
                  className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) { userDroppedFileRef.current = true; setPolarFile(f); } }}
                />
                <Upload size={11} />
                <span>{polarData ? t("polarDropToReplace") : t("polarDropZone")}</span>
              </div>
              {showPolar && polarData?.vmg_summary && (
                <div className="mt-2 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-900/40" data-testid="polar-table">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-slate-800/80 border-b border-slate-700/60">
                        <th rowSpan={2} className="py-1.5 px-1.5 text-center text-blue-300 font-bold">TWS</th>
                        <th colSpan={3} className="py-1 text-center text-green-400">{t("polarUpwind")}</th>
                        <th colSpan={3} className="py-1 text-center text-amber-400">{t("polarDownwind")}</th>
                      </tr>
                      <tr className="bg-slate-800/60 border-b border-slate-700/60">
                        {["TWA", "BS", "VMG", "TWA", "BS", "VMG"].map((h, i) => (
                          <th key={i} className="py-1 px-1 font-medium text-slate-400">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {POLAR_VMG_TWS_KEYS.map((tws) => (
                        <PolarVmgRow key={tws} tws={tws} entry={polarData.vmg_summary[tws]} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <AdminKeyField />
          </div>

          {skipperOrders && (
            <SkipperOrdersPanel
              orders={skipperOrders}
              profile={skipperProfile}
              onProfile={onSkipperProfile}
              onComfort={onSkipperComfort}
              onHorizon={onSkipperHorizon}
              onExpert={onSkipperExpert}
              onBoat={onSkipperBoat}
              onReset={onSkipperReset}
              suggest={skipperSuggest}
              onAcceptSuggest={onSkipperSuggestAccept}
              onDismissSuggest={onSkipperSuggestDismiss}
            />
          )}

          {maritimeLayers ? (
            <details className="px-4 py-3 border-t border-slate-700/60 group" data-testid="layers-drawer">
              <summary className="cursor-pointer select-none list-none flex items-center justify-between gap-2">
                <span className="text-[11px] font-semibold text-slate-200">{t("layersTitle")}</span>
                <span className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500">{layersOn ? t("layersOn", { n: layersOn }) : t("layersNone")}</span>
                  <span className="text-slate-500 group-open:rotate-90 transition-transform">›</span>
                </span>
              </summary>
              <div className="mt-2">
                <LayerToggles maritimeLayers={maritimeLayers} />
              </div>
            </details>
          ) : null}
        </div>
      </div>
    </>
  );
});
