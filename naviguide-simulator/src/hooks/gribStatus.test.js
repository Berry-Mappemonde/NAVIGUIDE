import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { officialGribStatus, officialGribWarning } from "./gribStatus.js";

describe("officialGribStatus", () => {
  it("reste pending sans position — pas absente à l’ouverture", () => {
    assert.equal(officialGribStatus({
      enabled: true,
      grib: { status: "absent" },
      pending: false,
      positioned: false,
    }), "pending");
    assert.equal(officialGribWarning({ enabled: true, status: "pending" }), null);
  });

  it("ready dès que le fichier est là", () => {
    assert.equal(officialGribStatus({
      enabled: true,
      grib: { status: "ready" },
      pending: false,
      positioned: true,
    }), "ready");
  });

  it("absente seulement après un fetch positionné raté", () => {
    assert.equal(officialGribStatus({
      enabled: true,
      grib: { status: "absent" },
      pending: false,
      positioned: true,
    }), "absent");
    assert.equal(officialGribWarning({ enabled: true, status: "absent" }), "dernière prévision absente");
  });
});
