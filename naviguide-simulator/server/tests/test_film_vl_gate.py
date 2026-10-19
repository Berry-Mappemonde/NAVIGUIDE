"""Revue Super VL : un défaut daté ne compte que s'il est sur l'image. Aucun appel Nebius."""
import io
import json
import shutil
import socket
import subprocess
from pathlib import Path

import pytest
from PIL import Image

import film_vl_gate as gate


def _png(color: tuple[int, int, int], size: int = 8) -> bytes:
    image = Image.new("RGB", (size, size), color)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _frame(color: tuple[int, int, int], visible_text: str = "") -> dict:
    return {"png": _png(color), "visible_text": visible_text}


APP = (30, 48, 72)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def _forbid_network(monkeypatch):
    def connect(self, address):
        raise AssertionError("réseau interdit")

    def create_connection(*args, **kwargs):
        raise AssertionError("réseau interdit")

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "create_connection", create_connection)


def test_module_sans_appel_reseau():
    src = Path(gate.__file__).read_text(encoding="utf-8")
    lowered = src.lower()
    assert "nebius" not in lowered
    assert "tokenfactory" not in lowered
    assert "urlopen" not in src
    assert "subprocess" not in src


def test_seuil_noir_et_blanc_de_la_relecture():
    # Vue d'application citée à tort comme écran noir : luminance 26, variance 86.
    assert gate.is_black_frame(26, 86) is False
    assert gate.is_white_frame(26, 86) is False
    assert gate.is_black_frame(0, 0) is True
    assert gate.is_white_frame(255, 0) is True
    black = gate.read_png(_png(BLACK))
    white = gate.read_png(_png(WHITE))
    app = gate.read_png(_png(APP))
    assert gate.is_black_frame(black["mean"], black["variance"]) is True
    assert gate.is_white_frame(white["mean"], white["variance"]) is True
    assert gate.is_black_frame(app["mean"], app["variance"]) is False
    assert gate.is_white_frame(app["mean"], app["variance"]) is False


def test_luminance_sans_pixels_ne_confirme_pas_le_noir():
    report = "- 01:50 : écran noir — bloquant\nVERDICT: KO"
    forged = {110: {"mean": 0, "variance": 0, "visible_text": "écran noir"}}
    with pytest.raises(gate.ReviewRefused) as caught:
        gate.accept_review(report, forged)
    assert caught.value.settled["counts"] is False
    assert "image illisible" in caught.value.settled["reason"]


def test_pass_avec_defaut_non_verifie_echoue(monkeypatch):
    _forbid_network(monkeypatch)
    report = "- 00:31 : Arcos — mineur\nVERDICT: PASS"
    frames = {31: _frame(APP, "La Rochelle → Ajaccio (Corse) · 1,820 nm")}
    with pytest.raises(gate.ReviewRefused) as caught:
        gate.accept_review(report, frames)
    settled = caught.value.settled
    assert settled["raw_verdict"] == "PASS"
    assert settled["verdict"] == gate.VERDICT_REFUSE
    assert settled["counts"] is False
    assert "Arcos absent" in settled["reason"]
    trial = settled["definition_trial"]
    assert trial["baseline_height"] == 720
    assert trial["baseline_fps"] == 5
    assert trial["trial_height"] == 1080
    assert trial["trial_fps"] == 10
    assert trial["trial_height"] > trial["baseline_height"]
    assert trial["trial_fps"] > trial["baseline_fps"]
    assert trial["baseline_vf"] == "scale=-2:720,fps=5"
    assert trial["trial_vf"] == "scale=-2:1080,fps=10"
    assert trial["paid_calls"] == 0
    assert trial["misreadings_decreased"] is None
    assert "non mesurées" in trial["note"]
    assert "1080" in trial["note"]


def test_pass_quand_le_nom_est_sur_l_image():
    report = "- 00:31 : Arcos — mineur\nVERDICT: PASS"
    frames = {31: _frame(APP, "Le libellé Arcos est lisible")}
    settled = gate.accept_review(report, frames)
    assert settled["verdict"] == "PASS"
    assert settled["counts"] is True
    assert settled["defects"][0]["verified"] is True


def test_pass_avec_un_seul_defaut_non_verifie_echoue():
    report = (
        "- 00:31 : Arcos — mineur\n"
        "- 07:25 : 24 August et 27 August — mineur\n"
        "VERDICT: PASS"
    )
    frames = {
        31: _frame(APP, "Ajaccio (Corse)"),
        445: _frame(APP, "On 24 August, the boat skirts Halifax. 27 August"),
    }
    with pytest.raises(gate.ReviewRefused) as caught:
        gate.accept_review(report, frames)
    defects = {d["mmss"]: d["verified"] for d in caught.value.settled["defects"]}
    assert defects["00:31"] is False
    assert defects["07:25"] is True


def test_dates_reelles_confirmees_sur_l_image():
    report = "- 07:25 : 24 août encore affiché, barre au 27 août — mineur\nVERDICT: PASS"
    frames = {445: _frame(APP, "24 août dans le popup, barre au 27 août")}
    settled = gate.accept_review(report, frames)
    assert settled["counts"] is True
    assert settled["defects"][0]["verified"] is True


def test_ko_date_absente_ne_compte_pas():
    report = "- 02:48 : la date affichée est le 9 juillet — bloquant\nVERDICT: KO"
    frames = {168: _frame(APP, "On 6 July, Spanish waters")}
    with pytest.raises(gate.ReviewRefused) as caught:
        gate.accept_review(report, frames)
    assert caught.value.settled["raw_verdict"] == "KO"
    assert caught.value.settled["verdict"] == gate.VERDICT_REFUSE
    assert "date 9 mois 7 absente" in caught.value.settled["reason"]


def test_ko_date_presente_compte():
    report = "- 02:48 : 6 juillet — bloquant\nVERDICT: KO"
    frames = {168: _frame(APP, "6 juillet")}
    settled = gate.accept_review(report, frames)
    assert settled["verdict"] == "KO"
    assert settled["counts"] is True


def test_ecran_noir_sur_une_vue_coloree_ne_compte_pas():
    report = "- 01:50 : écran noir — bloquant\nVERDICT: KO"
    frames = {110: _frame(APP, "Corse")}
    with pytest.raises(gate.ReviewRefused):
        gate.accept_review(report, frames)


def test_ecran_noir_confirme_par_les_pixels():
    report = "- 00:02 : écran noir — bloquant\nVERDICT: KO"
    frames = {2: _frame(BLACK, "le mot noir n'est pas écrit")}
    settled = gate.accept_review(report, frames)
    assert settled["verdict"] == "KO"
    assert settled["defects"][0]["verified"] is True


def test_carte_blanche_absente_refuse_le_pass():
    report = "- 01:40 : carte blanche — bloquant\nVERDICT: PASS"
    frames = {100: _frame(APP, "golfe du Lion")}
    with pytest.raises(gate.ReviewRefused) as caught:
        gate.accept_review(report, frames)
    assert "blanc absent" in caught.value.settled["reason"]


def test_about_blank_confirme_sur_image_blanche():
    report = "- 00:01 : about:blank — bloquant\nVERDICT: KO"
    frames = {1: _frame(WHITE, "")}
    settled = gate.accept_review(report, frames)
    assert settled["counts"] is True


def test_ko_mixte_garde_seulement_le_defaut_vu():
    report = (
        "- 01:28 : Venise — mineur\n"
        "- 08:31 : Mata-Utu — bloquant\n"
        "VERDICT: KO"
    )
    frames = {
        88: _frame(APP, "golfe du Lion, Calvi et Bastia"),
        511: _frame(APP, "the approach is by Mata-Utu"),
    }
    settled = gate.accept_review(report, frames)
    assert settled["verdict"] == "KO"
    by_time = {d["mmss"]: d["verified"] for d in settled["defects"]}
    assert by_time["01:28"] is False
    assert by_time["08:31"] is True


def test_ligne_rien_n_est_pas_un_defaut():
    settled = gate.accept_review("- 00:51 : rien\nVERDICT: PASS", {})
    assert settled["counts"] is True
    assert settled["defects"] == []


def test_image_absente_refuse_le_pass():
    report = "- 00:31 : Ploidy — mineur\nVERDICT: PASS"
    with pytest.raises(gate.ReviewRefused) as caught:
        gate.accept_review(report, {})
    assert "pas d'image" in caught.value.settled["reason"]


def test_rapport_par_morceaux():
    report = {
        "verdict": "PASS",
        "parts": [{"content": "- 04:06 : Tornados — mineur\nVERDICT: PASS"}],
    }
    frames = {246: _frame(APP, "Pointe-à-Pitre → Gustavia")}
    with pytest.raises(gate.ReviewRefused) as caught:
        gate.accept_review(report, frames)
    assert caught.value.settled["defects"][0]["t_s"] == 246
    assert "Tornados absent" in caught.value.settled["reason"]


def test_lecteur_d_image_injecte():
    seen = []

    def frames(t_s):
        seen.append(t_s)
        return _frame(APP, "Bilbos")

    settled = gate.accept_review("- 03:02 : Bilbos — mineur\nVERDICT: PASS", frames)
    assert seen == [182]
    assert settled["counts"] is True


def test_verdict_absent_echoue():
    with pytest.raises(gate.ReviewRefused) as caught:
        gate.accept_review("- 00:31 : Arcos — mineur", {31: _frame(APP, "Arcos")})
    assert caught.value.settled["counts"] is False
    assert "verdict absent" in caught.value.settled["reason"]


def test_essai_note_si_les_mauvaises_lectures_diminuent():
    down = gate.note_definition_trial(baseline_misreadings=6, trial_misreadings=2)
    assert down["misreadings_decreased"] is True
    assert down["paid_calls"] == 0
    assert "Elles diminuent." in down["note"]
    assert "1080p à 10 i/s" in down["note"]
    same = gate.note_definition_trial(baseline_misreadings=2, trial_misreadings=2)
    assert same["misreadings_decreased"] is False
    assert "Elles ne diminuent pas." in same["note"]
    up = gate.note_definition_trial(baseline_misreadings=2, trial_misreadings=5)
    assert up["misreadings_decreased"] is False
    unknown = gate.note_definition_trial(baseline_misreadings=4)
    assert unknown["misreadings_decreased"] is None
    assert "non mesurées" in unknown["note"]
    with pytest.raises(TypeError):
        gate.note_definition_trial(baseline_misreadings=True, trial_misreadings=1)
    with pytest.raises(ValueError):
        gate.note_definition_trial(baseline_misreadings=-1, trial_misreadings=0)


def test_filtre_essai_plus_haut_que_la_base():
    assert gate.scale_filter(720, 5) == "scale=-2:720,fps=5"
    assert gate.scale_filter(1080, 10) == "scale=-2:1080,fps=10"
    cmd = gate.ffmpeg_encode_cmd("film.mp4", "essai.mp4", height=1080, fps=10)
    assert "scale=-2:1080,fps=10" in cmd
    assert "-an" in cmd
    with pytest.raises(ValueError):
        gate.scale_filter(0, 5)


def _probe(path: Path) -> dict:
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=height,avg_frame_rate",
            "-of", "json", str(path),
        ],
        check=True, capture_output=True, text=True, timeout=20,
    )
    stream = json.loads(proc.stdout)["streams"][0]
    num, den = stream["avg_frame_rate"].split("/")
    return {"height": int(stream["height"]), "fps": float(num) / float(den)}


def test_encodage_local_plus_haut_que_720p_5ips(tmp_path):
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg absent : l'essai noté reste couvert sans encodage")
    src = tmp_path / "src.mp4"
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=0x1e2838:s=160x90:d=1",
            "-pix_fmt", "yuv420p", str(src),
        ],
        check=True, timeout=30,
    )
    probes = {}
    for name, height, fps in (("baseline", 720, 5), ("trial", 1080, 10)):
        dst = tmp_path / f"{name}.mp4"
        cmd = gate.ffmpeg_encode_cmd(str(src), str(dst), height=height, fps=fps)
        subprocess.run(cmd, check=True, timeout=30)
        probes[name] = _probe(dst)
    assert probes["baseline"]["height"] == 720
    assert probes["trial"]["height"] == 1080
    assert probes["baseline"]["fps"] == pytest.approx(5)
    assert probes["trial"]["fps"] == pytest.approx(10)
    note = gate.note_definition_trial(
        measured_baseline=probes["baseline"],
        measured_trial=probes["trial"],
    )
    assert note["paid_calls"] == 0
    assert note["misreadings_decreased"] is None
    assert note["measured"]["trial_height"] == 1080
    assert note["measured"]["trial_fps"] == pytest.approx(10)
    assert "Mesuré : essai 1080p à 10 i/s, base 720p à 5 i/s." in note["note"]
    assert "non mesurées" in note["note"]
    with pytest.raises(ValueError):
        gate.note_definition_trial(
            measured_baseline={"height": 1080, "fps": 10},
            measured_trial={"height": 720, "fps": 5},
        )
