import { useEffect, useRef, useState } from "react";
import { Anchor, CheckCircle2, ChevronLeft, ChevronRight, Compass, Loader2, TriangleAlert, Upload } from "lucide-react";
import { useLang } from "../i18n/LangContext.jsx";

const POLAR_API_URL = import.meta.env.VITE_POLAR_API_URL ?? "";
const POLAR_EXPEDITION = "berry-mappemonde-2026"; // pragma: allowlist secret
const POLAR_VMG_TWS_KEYS = ["8", "10", "12", "16", "20", "25"];
const DEFAULT_POLAR_URL = "/Leopard46_Standard_Sails.csv";
const DEFAULT_POLAR_NAME = "Leopard 46";

function kts(v) { return v != null ? `${Number(v).toFixed(1)} kt` : "—"; }
function deg(v) { return v != null ? `${Math.round(v)}°` : "—"; }

function PolarStatusBadge({ status, detail }) {
  const { t } = useLang();
  const cfg = {
    uploading: { icon: <Loader2 size={12} className="animate-spin" />, color: "text-blue-400", bg: "bg-blue-900/30", text: t("polarAnalyzing") },
    success: { icon: <CheckCircle2 size={12} />, color: "text-green-400", bg: "bg-green-900/30", text: t("polarLoaded") },
    error: { icon: <TriangleAlert size={12} />, color: "text-red-400", bg: "bg-red-900/30", text: t("polarFailed") },
  };
  if (!status) return null;
  const c = cfg[status] ?? cfg.error;
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${c.bg} ${c.color} text-xs`}>
      {c.icon}
      <span className="font-medium">{c.text}</span>
      {detail && <span className="text-slate-400 truncate ml-1">— {detail}</span>}
    </div>
  );
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

function StatRow({ icon, label, value }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-700/40 last:border-0">
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span className="text-slate-500">{icon}</span>
        {label}
      </div>
      <span className="text-xs font-semibold text-white">{value}</span>
    </div>
  );
}

function Toggle({ labelLeft, labelRight, active, onChange }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-slate-400">{active ? labelRight : labelLeft}</span>
      <button
        type="button"
        onClick={() => onChange(!active)}
        className={`w-10 h-5 rounded-full relative transition-colors ${active ? "bg-sky-500" : "bg-slate-600"}`}
      >
        <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${active ? "left-5" : "left-0.5"}`} />
      </button>
    </div>
  );
}

export function ToolsSidebar({
  segments, points, open, onToggle,
  isLightMode, onLightModeChange,
  polarData, onPolarDataLoaded,
  routeDistanceNm, routeSegmentCount,
}) {
  const { lang, switchLang, t } = useLang();
  const [polarFile, setPolarFile] = useState(null);
  const [polarUploadStatus, setPolarUploadStatus] = useState(null);
  const [polarUploadDetail, setPolarUploadDetail] = useState("");
  const [isDragging, setIsDragging] = useState(false);
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
        const res = await fetch(DEFAULT_POLAR_URL);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        const file = new File([blob], "Leopard46_Standard_Sails.csv", { type: "text/csv" });
        const form = new FormData();
        form.append("file", file);
        form.append("expedition_id", POLAR_EXPEDITION);
        form.append("boat_name", DEFAULT_POLAR_NAME);
        const uploadRes = await fetch(`${POLAR_API_URL}/api/v1/polar/upload`, { method: "POST", body: form });
        const data = await uploadRes.json();
        if (!uploadRes.ok) throw new Error(data.detail ?? `HTTP ${uploadRes.status}`);
        if (userDroppedFileRef.current) return;
        onPolarDataLoaded({
          expedition_id: data.expedition_id,
          boat_name: data.boat_name,
          grid_shape: data.grid_shape,
          vmg_summary: data.vmg_summary,
          created_at: data.created_at,
        });
        setPolarUploadStatus("success");
        setPolarUploadDetail(data.boat_name);
      } catch (err) {
        if (userDroppedFileRef.current) return;
        setPolarUploadStatus("error");
        setPolarUploadDetail(String(err?.message ?? err));
      }
    };
    loadDefaultPolars();
  }, [polarData, onPolarDataLoaded]);

  const handlePolarUpload = async (f) => {
    setPolarUploadStatus("uploading");
    setPolarUploadDetail("");
    const form = new FormData();
    form.append("file", f);
    form.append("expedition_id", POLAR_EXPEDITION);
    try {
      const res = await fetch(`${POLAR_API_URL}/api/v1/polar/upload`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
      onPolarDataLoaded({
        expedition_id: data.expedition_id,
        boat_name: data.boat_name,
        grid_shape: data.grid_shape,
        vmg_summary: data.vmg_summary,
        created_at: data.created_at,
      });
      setPolarUploadStatus("success");
      setPolarUploadDetail(data.boat_name);
    } catch (err) {
      setPolarUploadStatus("error");
      setPolarUploadDetail(String(err.message ?? err));
    }
  };

  const maritimeSegs = segments.filter((s) => !s.nonMaritime && s.coords?.length > 0);
  const overlandSegs = segments.filter((s) => s.nonMaritime && s.coords?.length > 0);
  const totalSegments = maritimeSegs.length + overlandSegs.length;
  const totalPoints = segments.reduce((acc, s) => acc + (s.coords?.length ?? 0), 0);

  return (
    <>
      <button
        onClick={onToggle}
        className={`naviguide-sidebar-toggle absolute top-4 z-30 bg-slate-900/95 text-white
          rounded-full w-12 h-12 flex items-center justify-center shadow-lg
          border-2 border-sky-400/70 shadow-sky-900/40
          hover:bg-slate-800 transition-all duration-300 ${open ? "right-[322px]" : "right-4"}`}
        title={open ? t("hideToolsPanel") : t("showToolsPanel")}
      >
        {open ? <ChevronRight size={22} /> : <ChevronLeft size={22} />}
      </button>

      <div
        className={`naviguide-sidebar-panel absolute top-0 right-0 h-full z-20 flex flex-col bg-slate-900/97
          border-l-2 border-sky-400/40 shadow-2xl transition-transform duration-300
          ${open ? "translate-x-0" : "translate-x-full"}`}
        style={{ width: 320 }}
      >
        <div className="flex-1 overflow-y-auto sidebar-scroll">
          <div className="px-4 pt-4 pb-1">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{t("language")}</span>
              <div className="flex bg-slate-800 rounded-full p-0.5 gap-0.5">
                <button onClick={() => switchLang("en")} className={`px-3 py-1 rounded-full text-xs font-bold ${lang === "en" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"}`}>EN</button>
                <button onClick={() => switchLang("fr")} className={`px-3 py-1 rounded-full text-xs font-bold ${lang === "fr" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"}`}>FR</button>
              </div>
            </div>
          </div>

          <div className="px-4 pb-3 border-b border-slate-700/60 space-y-3">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{t("modes")}</div>
            <Toggle labelLeft={t("dark")} labelRight={t("light")} active={isLightMode} onChange={onLightModeChange} />
          </div>

          <div className="px-4 py-3 border-b border-slate-700/60">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Anchor size={11} className="text-blue-400" />
              {t("routeSummary")}
            </div>
            <div className="bg-slate-800/60 rounded-xl px-3 py-1 border border-slate-700/40">
              <StatRow icon="📏" label={t("totalDistanceNm")} value={routeDistanceNm != null ? `${Number(routeDistanceNm).toLocaleString()} nm` : "—"} />
              <StatRow icon="🗺️" label={t("totalSegments")} value={routeSegmentCount ?? totalSegments} />
              <StatRow icon="⚓" label={t("maritimeLegs")} value={maritimeSegs.length} />
              <StatRow icon="🛣️" label={t("overlandLegs")} value={overlandSegs.length} />
              <StatRow icon="📍" label={t("waypoints")} value={points.length} />
              <StatRow icon="🔢" label={t("routePoints")} value={totalPoints.toLocaleString()} />
            </div>
          </div>

          <div className="px-4 py-4 space-y-3">
            <PolarStatusBadge status={polarUploadStatus} detail={polarUploadDetail} />
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Compass size={11} className="text-blue-400" />
              {t("polarSection")}
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
              className={`flex flex-col items-center justify-center gap-1.5 p-4 border-2 border-dashed rounded-xl cursor-pointer
                ${isDragging ? "border-blue-400 bg-blue-900/20" : "border-slate-600 hover:border-slate-500 bg-slate-800/40"}`}
            >
              <input
                ref={polarFileInputRef}
                type="file"
                accept=".pdf,.csv,.xlsx,.xls"
                className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) { userDroppedFileRef.current = true; setPolarFile(f); } }}
              />
              {polarUploadStatus === "uploading"
                ? <Loader2 size={18} className="animate-spin text-blue-400" />
                : <Upload size={18} className="text-slate-500" />}
              <span className="text-xs text-slate-400">{t("polarDropZone")}</span>
              <span className="text-xs text-slate-600">{t("polarFormats")}</span>
            </div>
            {polarUploadStatus === "error" && (
              <p className="text-xs text-red-400">{t("polarUploadErrorPrefix")} — {polarUploadDetail}</p>
            )}
            {polarData?.vmg_summary && (
              <div className="overflow-x-auto rounded-xl border border-slate-700/40 bg-slate-800/40">
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
        </div>
      </div>
    </>
  );
}
