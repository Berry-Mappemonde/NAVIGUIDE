#!/usr/bin/env node
/**
 * Lot R13 — redites i18n (fr.js).
 * Node, sans dépendance : groupes de ≥ 2 mots (hors mots vides) présents
 * dans ≥ 2 valeurs, et valeurs identiques sous deux clés. Tri par fréquence.
 */
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const STOP = new Set([
  "le", "la", "de", "du", "des", "et", "à", "en", "un", "une", "sur", "par", "au", "aux", "pour",
]);

const here = dirname(fileURLToPath(import.meta.url));
const frPath = join(here, "../src/i18n/fr.js");
const { default: fr } = await import(pathToFileURL(frPath).href);

function wordsOf(value) {
  return String(value)
    .normalize("NFC")
    .toLowerCase()
    .match(/[a-zàâäéèêëïîôùûüçœæ0-9’']+/gi) || [];
}

function contentWords(value) {
  return wordsOf(value).filter((w) => !STOP.has(w.replace(/’/g, "'")));
}

function ngrams(tokens, min = 2) {
  const out = [];
  for (let n = min; n <= tokens.length; n += 1) {
    for (let i = 0; i + n <= tokens.length; i += 1) {
      out.push(tokens.slice(i, i + n).join(" "));
    }
  }
  return out;
}

export function analyze(dict) {
  const entries = Object.entries(dict).filter(([, v]) => typeof v === "string" && v.trim());
  const byValue = new Map();
  const byGroup = new Map();

  for (const [key, value] of entries) {
    const bucket = byValue.get(value) || [];
    bucket.push(key);
    byValue.set(value, bucket);

    const seen = new Set();
    for (const g of ngrams(contentWords(value))) {
      if (seen.has(g)) continue;
      seen.add(g);
      const rec = byGroup.get(g) || { group: g, keys: [], values: [] };
      rec.keys.push(key);
      rec.values.push(value);
      byGroup.set(g, rec);
    }
  }

  const identical = [...byValue.entries()]
    .filter(([, keys]) => keys.length >= 2)
    .map(([value, keys]) => ({ value, keys, n: keys.length }))
    .sort((a, b) => b.n - a.n || a.value.localeCompare(b.value, "fr"));

  const groups = [...byGroup.values()]
    .filter((rec) => rec.keys.length >= 2)
    .map((rec) => ({ ...rec, n: rec.keys.length }))
    .sort((a, b) => b.n - a.n || b.group.split(" ").length - a.group.split(" ").length || a.group.localeCompare(b.group, "fr"));

  return { identical, groups };
}

function quote(s) {
  return JSON.stringify(s);
}

export function formatReport(report) {
  const lines = [];
  lines.push("# Redites i18n (src/i18n/fr.js)");
  lines.push("");
  lines.push("## Valeurs identiques sous deux clés ou plus");
  if (!report.identical.length) {
    lines.push("(aucune)");
  } else {
    for (const row of report.identical) {
      lines.push(`${row.n}\t${quote(row.value)}`);
      lines.push(`\t${row.keys.join(", ")}`);
    }
  }
  lines.push("");
  lines.push("## Groupes de ≥ 2 mots (hors mots vides) dans ≥ 2 valeurs");
  if (!report.groups.length) {
    lines.push("(aucun)");
  } else {
    for (const row of report.groups) {
      lines.push(`${row.n}\t${quote(row.group)}`);
      lines.push(`\t${row.keys.join(", ")}`);
    }
  }
  lines.push("");
  return lines.join("\n");
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  const report = analyze(fr);
  process.stdout.write(formatReport(report));
}
