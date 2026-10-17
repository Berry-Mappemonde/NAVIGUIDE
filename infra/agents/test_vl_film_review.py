"""Lot VR1 : KO de mouvement hors parcours 🤖 ; VL simulé sans fait de mer."""
from pathlib import Path

import review_agent as ra
import run_lots as rl
import vl_film_review as vl


KO_CAMERA = "- [ ] KO : la caméra décroche"


def test_extrait_ko_sans_titre_bot():
    comments = [{"body": f"Revue manuelle\n{KO_CAMERA}\n"}]
    assert vl.collect_movement_kos(comments) == [KO_CAMERA]


def test_ignore_ligne_sans_prefixe():
    comments = [{
        "body": (
            "la caméra décroche\n"
            "KO : le zoom saute\n"
            "- [x] KO : figé\n"
            "- la caméra décroche\n"
        ),
    }]
    assert vl.collect_movement_kos(comments) == []


def test_parcours_section_ne_prend_pas_ce_ko():
    """Constat VR1 : parcours_section exige 🤖 + « — KO » ; une ligne « - [ ] KO : » seule ne passe pas."""
    comments = [{"body": KO_CAMERA, "html_url": "https://example.test/c/1", "created_at": "2026-10-16T12:00:00Z"}]

    class _Http:
        def github(self, path, method="GET", body=None):
            return comments

    state = rl.State(done={"VR1": {"pr": "https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/1"}})
    text = "\n".join(ra.parcours_section(state, ["VR1"], _Http()))
    assert KO_CAMERA not in text
    assert "Absent" in text or "aucun KO" in text


def test_vl_simule_qui_invente_un_port_est_rejete(monkeypatch):
    monkeypatch.setenv(vl.ENV_FLAG, "1")
    monkeypatch.delenv("CI", raising=False)
    telemetry = {"frames": [{"dt": 16.6, "zoom": 4, "bx": 720, "by": 400}]}

    def fake_vl(prompt, images):
        assert "saccade" in prompt
        return (
            "Le bateau longe Ajaccio, mer belle, 15 kn.\n"
            f"{KO_CAMERA}\n"
            "- [ ] KO : le zoom saute à Ajaccio\n"
            "- [ ] KO : saccade au zoom 9\n"
        )

    comment = vl.review_film(
        images=["shot.jpg"],
        telemetry=telemetry,
        subtitle="Cap sur Ajaccio.",
        diff_files=["naviguide-simulator/src/map/filmCamera.js"],
        vl_call=fake_vl,
    )
    assert KO_CAMERA in comment
    assert "Ajaccio" not in comment
    assert "15 kn" not in comment
    assert "mer" not in comment
    assert "zoom 9" not in comment  # 9 n'est pas dans la télémétrie


def test_eteint_sans_variable(monkeypatch):
    monkeypatch.delenv(vl.ENV_FLAG, raising=False)
    monkeypatch.delenv("CI", raising=False)
    called = []
    out = vl.review_film(
        images=["shot.jpg"],
        telemetry={"zoom": 4},
        subtitle="",
        diff_files=["filmCamera.js"],
        vl_call=lambda *a: called.append(1) or KO_CAMERA,
    )
    assert out == ""
    assert called == []


def test_diff_hors_film_nappelle_pas(monkeypatch):
    monkeypatch.setenv(vl.ENV_FLAG, "1")
    monkeypatch.delenv("CI", raising=False)
    called = []
    out = vl.review_film(
        images=["shot.jpg"],
        telemetry={"zoom": 4},
        subtitle="",
        diff_files=["infra/agents/llm_budget.py"],
        vl_call=lambda *a: called.append(1) or KO_CAMERA,
    )
    assert out == ""
    assert called == []


def test_ci_nappelle_pas_meme_si_allume(monkeypatch):
    monkeypatch.setenv(vl.ENV_FLAG, "1")
    monkeypatch.setenv("CI", "true")
    called = []
    out = vl.review_film(
        images=["shot.jpg"],
        telemetry={"zoom": 4},
        subtitle="",
        diff_files=["filmCamera.js"],
        vl_call=lambda *a: called.append(1) or KO_CAMERA,
    )
    assert out == ""
    assert called == []


def test_call_vl_refuse_token_factory(monkeypatch):
    monkeypatch.setenv(vl.ENV_URL, "https://api.tokenfactory.example/v1/chat/completions")
    try:
        vl.call_vl("prompt", [])
    except RuntimeError as e:
        assert "Token Factory" in str(e)
    else:
        raise AssertionError("Token Factory aurait dû être refusé")


def test_run_lots_nappelle_pas_vl():
    src = Path(__file__).with_name("run_lots.py").read_text(encoding="utf-8")
    assert "vl_film_review" not in src
    assert "NAVIGUIDE_VL_REVIEW" not in src


def test_build_prompt_ajoute_ko_mouvement_au_reviseur(tmp_path, monkeypatch):
    monkeypatch.setattr(ra, "lot_texts", lambda ids: {})
    monkeypatch.setattr(ra, "parcours_section", lambda *a, **k: [])
    monkeypatch.setattr(rl, "fetch_pr", lambda *a, **k: {"body": "corps", "title": "VR1"})
    import review_collect as rc
    monkeypatch.setattr(rc, "_TRUSTED", set())

    comments = [{"body": f"sans titre bot\n{KO_CAMERA}\n", "user": {"login": "x"}}]

    class _Http:
        def github(self, path, method="GET", body=None):
            if "/comments" in path:
                return comments
            return {"body": "corps", "title": "VR1"}

    state = rl.State(
        done={"VR1": {
            "status": "FINISHED",
            "pr": "https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/999",
            "branch": "fix/lot-vr1-vl-revue-film",
        }},
        last_branch="fix/lot-vr1-vl-revue-film",
        last_lot="VR1",
    )
    prompt = ra.build_prompt(state, ["VR1"], tmp_path, tmp_path, "cursor-grok-4.6-xhigh-fast", _Http())
    assert KO_CAMERA in prompt
    assert "KO de mouvement" in prompt
    assert "pas un canal à part" in prompt
    assert "lot RC" in prompt
