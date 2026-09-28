#!/usr/bin/env node
// Résumé d'étape GitHub : N specs, rouges nommés, poste (skipped CI).
import { readFileSync } from "node:fs";

const path = process.argv[2] || "test-results/e2e.json";
let report;
try {
  report = JSON.parse(readFileSync(path, "utf8"));
} catch {
  console.log("## Recette automatique Playwright\n\nrapport JSON absent.");
  process.exit(0);
}

const tests = [];
for (const suite of report.suites || []) walk(suite);

function walk(suite) {
  for (const spec of suite.specs || []) {
    for (const t of spec.tests || []) {
      const result = (t.results || [])[0] || {};
      const status = t.status || result.status || "unknown";
      const annotations = (t.annotations || []).map((a) => a.type || a.description || "").join(" ");
      tests.push({
        title: spec.title,
        file: spec.file || suite.file || "",
        status,
        annotations,
      });
    }
  }
  for (const child of suite.suites || []) walk(child);
}

const failed = tests.filter((t) => t.status === "unexpected" || t.status === "failed");
const skipped = tests.filter((t) => t.status === "skipped");
const poste = skipped.filter((t) => /poste/i.test(t.annotations));
const passed = tests.filter((t) => t.status === "expected" || t.status === "passed");

console.log("## Recette automatique Playwright");
console.log("");
console.log(`**${failed.length} spec rouge**, ${tests.length} specs, ${poste.length} poste, ${skipped.length} ignorés, ${passed.length} verts.`);
console.log("");
if (failed.length) {
  console.log("### Specs rouges");
  for (const t of failed) console.log(`- \`${t.file}\` — ${t.title}`);
} else {
  console.log("0 spec rouge.");
}
if (poste.length) {
  console.log("");
  console.log("### Specs poste (ignorés en CI)");
  for (const t of poste) console.log(`- \`${t.file}\` — ${t.title}`);
}
