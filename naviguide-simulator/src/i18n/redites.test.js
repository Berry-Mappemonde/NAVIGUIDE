import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { analyze, formatReport } from "../../scripts/redites.mjs";
import fr from "./fr.js";

describe("scripts/redites.mjs (lot R13)", () => {
  it("liste les valeurs identiques et les groupes de ≥ 2 mots, triés par fréquence", () => {
    const report = analyze(fr);
    assert.ok(report.identical.length >= 1, "au moins une valeur partagée");
    const hide = report.identical.find((row) => row.value === "Masquer le panneau");
    assert.ok(hide, "« Masquer le panneau » sous plusieurs clés");
    assert.ok(hide.n >= 2);
    assert.ok(hide.keys.includes("hideSidebar"));
    assert.ok(report.groups.length >= 1, "au moins un groupe de mots partagé");
    const first = report.groups[0];
    assert.ok(first.n >= 2);
    assert.ok(first.group.split(" ").length >= 2);
    for (let i = 1; i < report.groups.length; i += 1) {
      assert.ok(report.groups[i - 1].n >= report.groups[i].n, "groupes triés par fréquence");
    }
    const text = formatReport(report);
    assert.match(text, /Valeurs identiques/);
    assert.match(text, /Groupes de ≥ 2 mots/);
  });
});
