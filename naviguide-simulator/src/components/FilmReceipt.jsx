/**
 * Idée n° 3 : reçu « How this film was made » / « Comment ce film a été fait ».
 * Repliable, sous le film Rédigé. Seulement les compteurs servis par le serveur
 * (receipt) et le nombre de sources Tavily réellement affichées. Rien d'autre.
 */
import { receiptLines, receiptModelRows } from "../utils/filmReceipt.js";

function formatAt(at, lang) {
  const d = new Date(at);
  if (Number.isNaN(d.getTime())) return "";
  try {
    return d.toLocaleString(lang === "en" ? "en-GB" : "fr-FR", {
      dateStyle: "medium", timeStyle: "short", timeZone: "UTC",
    }) + " UTC";
  } catch {
    return d.toISOString();
  }
}

export default function FilmReceipt({ receipt, webSourceCount = 0, t, lang = "fr" }) {
  if (!receipt) return null;
  const models = receiptModelRows(receipt);
  const lines = receiptLines(receipt, webSourceCount);
  if (!models.length && !lines.length) return null;
  const at = receipt.at ? formatAt(receipt.at, lang) : "";
  return (
    <details
      data-testid="film-receipt"
      className="min-w-0 max-w-full whitespace-normal break-words text-[10px] leading-snug text-white/85"
    >
      <summary className="cursor-pointer select-none underline underline-offset-2">
        {t("filmReceiptTitle")}
      </summary>
      <div className="mt-1 space-y-0.5">
        <div>{t("filmReceiptIntro")}</div>
        <ul data-testid="film-receipt-models" className="list-disc pl-4">
          {models.map((m) => (
            <li key={m.key} data-testid="film-receipt-model">
              {m.cached
                ? t("filmReceiptModelCached", { model: t(m.key), n: m.calls, cached: m.cached })
                : t("filmReceiptModel", { model: t(m.key), n: m.calls })}
            </li>
          ))}
        </ul>
        <ul data-testid="film-receipt-steps" className="list-disc pl-4">
          {lines.map((l) => (
            <li key={l.key} data-testid={`film-receipt-${l.key}`}>{t(l.key, l.vars)}</li>
          ))}
        </ul>
        {at ? <div className="text-white/60">{t("filmReceiptAt", { at })}</div> : null}
      </div>
    </details>
  );
}
