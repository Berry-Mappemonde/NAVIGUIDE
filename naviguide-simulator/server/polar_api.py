"""Polar upload / lecture — sans chat. Extrait de polar_api/main.py."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from polar_engine import PolarData, parse_polar_csv, parse_polar_excel, parse_polar_pdf

POLAR_DATA_DIR = Path(__file__).resolve().parent / "polar_data"
POLAR_DATA_DIR.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("naviguide-simulator.polar")
router = APIRouter()


def _polar_path(expedition_id: str) -> Path:
    safe = expedition_id.replace("/", "_").replace("\\", "_").replace(" ", "_")
    return POLAR_DATA_DIR / f"polar_{safe}.json"


def _serialize_polar(polar: PolarData, expedition_id: str) -> Dict[str, Any]:
    full_grid = polar.generate_full_grid()
    vmg_summary = polar.summary()
    return {
        "expedition_id": expedition_id,
        "boat_name": polar.boat_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "grid_shape": [181, 61],
        "raw": {
            "twa_rows": polar.twa_rows,
            "tws_cols": polar.tws_cols,
            "matrix": polar.matrix.tolist(),
        },
        "grid": full_grid.tolist(),
        "vmg_summary": {
            str(tws): {
                "upwind": d["upwind"],
                "downwind": d["downwind"],
                "gybe_angle": d["gybe_angle"],
            }
            for tws, d in vmg_summary.items()
        },
    }


def _load_polar_data(expedition_id: str) -> PolarData:
    dest = _polar_path(expedition_id)
    if not dest.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No polar data found for expedition '{expedition_id}'.",
        )
    with open(dest, encoding="utf-8") as fh:
        data = json.load(fh)
    raw = data["raw"]
    return PolarData(raw["twa_rows"], raw["tws_cols"], raw["matrix"], boat_name=data.get("boat_name", "Boat"))


@router.post("/api/v1/polar/upload")
async def upload_polar(
    file: UploadFile = File(...),
    expedition_id: str = Form(...),
    boat_name: Optional[str] = Form(None),
):
    fname = (file.filename or "").lower()
    allowed = (".pdf", ".csv", ".xlsx", ".xls")
    if not any(fname.endswith(ext) for ext in allowed):
        raise HTTPException(status_code=400, detail="Accepted formats: PDF, CSV, XLSX, XLS.")

    bname = boat_name or expedition_id
    raw_bytes = await file.read()
    try:
        if fname.endswith(".pdf"):
            polar = parse_polar_pdf(raw_bytes, boat_name=bname)
        elif fname.endswith(".csv"):
            polar = parse_polar_csv(raw_bytes, boat_name=bname)
        else:
            polar = parse_polar_excel(raw_bytes, boat_name=bname)
    except Exception as exc:
        log.error("File parsing failed: %s", exc)
        raise HTTPException(status_code=422, detail=f"Parsing error: {exc}") from exc

    try:
        data = _serialize_polar(polar, expedition_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Grid generation error: {exc}") from exc

    dest = _polar_path(expedition_id)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    return {
        "status": "ok",
        "expedition_id": expedition_id,
        "boat_name": bname,
        "grid_shape": data["grid_shape"],
        "raw_rows": len(polar.twa_rows),
        "raw_cols": len(polar.tws_cols),
        "vmg_summary": data["vmg_summary"],
        "created_at": data["created_at"],
    }


@router.api_route("/api/v1/polar/chat", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def polar_chat_removed():
    raise HTTPException(status_code=404, detail="Polar chat is not part of the simulator.")


@router.get("/api/v1/polar/{expedition_id}")
def get_polar(expedition_id: str):
    dest = _polar_path(expedition_id)
    if not dest.exists():
        raise HTTPException(status_code=404, detail=f"No polar data found for expedition '{expedition_id}'.")
    with open(dest, encoding="utf-8") as fh:
        return json.load(fh)


@router.get("/api/v1/polar/{expedition_id}/summary")
def get_polar_summary(expedition_id: str):
    dest = _polar_path(expedition_id)
    if not dest.exists():
        raise HTTPException(status_code=404, detail=f"No polar data found for expedition '{expedition_id}'.")
    with open(dest, encoding="utf-8") as fh:
        data = json.load(fh)
    return {
        "expedition_id": data["expedition_id"],
        "boat_name": data["boat_name"],
        "created_at": data["created_at"],
        "grid_shape": data["grid_shape"],
        "vmg_summary": data["vmg_summary"],
    }


@router.get("/api/v1/polar/{expedition_id}/speed")
def get_polar_speed(expedition_id: str, twa: float, tws: float):
    polar = _load_polar_data(expedition_id)
    return {
        "expedition_id": expedition_id,
        "twa": twa,
        "tws": tws,
        "speed": float(polar.speed(twa, tws)),
    }
