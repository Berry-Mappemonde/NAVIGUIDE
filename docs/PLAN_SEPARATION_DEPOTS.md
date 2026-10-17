# Mono-repo split — Blue Intelligence and NAVIGUIDE

Plan date: 17 October 2026. Execute it **over the weekend of 17–18 October 2026**, before the GenAI.works hackathon opens (22 October 2026 00:00 UTC).

This weekend covers the repository split, pointing the VPS at the new repositories, and the tests that make it reasonable to archive `Blue-Intelligence-Map`. No `agent_poe` commit. Graded GenAI code starts on 22 October 2026 at 00:00 UTC, in the Blue Intelligence repository that is already in production.

Each hackathon then names **its** repository on its form:

| Hackathon | Repository the jury reads | Plan |
|---|---|---|
| Nebius × NVIDIA (Devpost) | NAVIGUIDE | [PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md](PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md) |
| GenAI.works — Open Agent Hackathon | Blue Intelligence | [PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md](PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md) |

The mono-repo `Berry-Mappemonde/Blue-Intelligence-Map` (1,249 commits as of 16 October) currently mixes both products. Leave that history in place. Archive it only when the §6 checklist is green. Until then it stays the backup copy, and its deploy workflow is disabled so a push there cannot overwrite the VPS.

---

## 1. What is coupled, and what is not

The simulator does not import `backend/app`. It calls the API already in production:

- `naviguide-simulator/server/bi_proxy.py` and `server/main.py`: `BI_API_URL`, default `https://blueintelligence.online/api`;
- layers `/proxy/catalog/poe`, `marinas`, `capitaineries`, `amp`, `ports` (WPI), EEZ tiles;
- `server/ici_engine.py`: `BI_LIVE_API` to the same host.

After the split, those URLs stay. Simulator code is not copied into the Blue Intelligence repository.

The old `naviguide/` folder is a leftover from before the simulator. It goes with the NAVIGUIDE repository, not with Blue Intelligence.

Current CI (`.github/workflows/ci.yml`) tests the BI frontend and, when a PR touches it, the simulator. It does not run backend pytest. The new BI repository will need that job; it is not a prerequisite for the 27 October demo.

## 2. Target repositories

| Repository | Contents | Remote |
|---|---|---|
| Blue Intelligence (GenAI.works hackathon) | `backend/`, `frontend/`, product `infra/` (`blue-intelligence` service, nginx, backups), PoE and BI architecture `docs/`, BI data `scripts/`, `seed/` | new repository |
| NAVIGUIDE (Nebius × NVIDIA hackathon) | `naviguide-simulator/`, `naviguide/`, `infra/vps/naviguide/`, simulator docs | new repository |

The GenAI hackathon repository **is** the Blue Intelligence repository. There is no third “mini demo” repo: judges must see the pre-existing code next to the new module, with a README that separates the two.

## 3. Git history

`git filter-repo` rewrites commits. Run it on a **mirror clone in a temporary directory**, then push to the new remote. BI file history is kept. SHAs change, because this is a different repository.

Paths to keep for Blue Intelligence:

```text
backend/
frontend/
infra/
docs/
scripts/
seed/
README.md
LICENSE
LICENSE-MIT
LICENSE-APACHE
```

Paths to leave out of Blue Intelligence (they go to NAVIGUIDE):

```text
naviguide-simulator/
naviguide/
Archives/
.cursor/
```

`infra/vps/naviguide/` serves the simulator. First commit **after** the filter, the same weekend: remove that subdirectory from the BI repository. That is split hygiene, before 22 October, not an agent feature.

Docs are mixed (simulator plans and the PoE brief live in the same `docs/`). Keep them in the BI repository so history stays intact, and point the README at the documents the GenAI jury needs: [PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md](PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md), `docs/CAHIER_DES_CHARGES_POE.md`, `docs/ARCHITECTURE.md`. The NAVIGUIDE repository carries the simulator docs, including [PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md](PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md) and `docs/HACKATHON_DEVPOST_SOUMISSION.md`.

Command sketch (weekend of 17–18 October) — Blue Intelligence first:

```bash
# temporary directory, outside the working clone
git clone --mirror git@github.com:Berry-Mappemonde/Blue-Intelligence-Map.git /tmp/bi-mirror
cd /tmp/bi-mirror
git filter-repo \
  --path backend/ --path frontend/ --path infra/ \
  --path docs/ --path scripts/ --path seed/ \
  --path README.md --path LICENSE --path LICENSE-MIT --path LICENSE-APACHE
git remote add origin git@github.com:Berry-Mappemonde/<new-bi-repo>.git
git push --mirror origin
```

Before the push, check that `git log -- backend/app/services/poe_pipeline.py` reaches back before September 2026. That is the history proof the GenAI rules ask for: pre-existing code must be visible as such.

Build the NAVIGUIDE repository the same way, on a **different** mirror clone, keeping `naviguide-simulator/`, `naviguide/`, `infra/vps/naviguide/`, and the simulator docs. Do not filter both repositories inside the same `/tmp` directory.

## 4. Dependencies to cut

| Link | Action over the weekend of 17–18 October |
|---|---|
| Simulator HTTP calls to `blueintelligence.online` | **Keep them.** The simulator keeps reading the production API. |
| `infra/vps/deploy-app.sh` sets a local VPS `MONGO_URL` | Stays in the BI repository. Do not point it at Atlas. |
| `backend/.env` on the Mac still points at MongoDB Atlas | Atlas has been frozen since 10 September 2026. The new repository documents the **VPS** database as the live one. No secret in git (`.env*` is already ignored). |
| EEZ and route GeoJSON | Already in `backend/data/`. The simulator has its own copies. No cross-import. |
| NVIDIA, Zetaris, Toloka, Nebius, Tavily keys | Stay in local `.env` files and in the VPS secret store. Never in the README. |

## 5. Risks

| Risk | Mitigation |
|---|---|
| `filter-repo` run on the working clone, local history lost | Mirror clone in `/tmp` only. The old remote is not rewritten. |
| Large files (`eez_world_map.geojson` ~18 MB, climatology atlas) rejected by GitHub | The product repository keeps them. If the push fails, Git LFS on those binaries only, the same weekend. |
| An old secret in history | `git log -S` on key patterns **without printing the secrets**, before the public push. If a secret was ever committed, remove it from the new repository and rotate it. |
| Production breaks when paths change | Two new directories on the VPS, systemd paths and `deploy-app.sh` updated, a blank deploy, then the §6 list. If a test fails, point the services back at `~/blue-intelligence-map`, which is still on disk. Do not archive. |
| The GenAI jury treats the whole backend as hackathon work | README: pre-existing / new table. The only new package is `backend/app/agent_poe/`. |
| The Devpost form still points at the mono-repo | As soon as the NAVIGUIDE repository exists, the public URL on the form becomes that repository. Paste-ready text is in `HACKATHON_DEVPOST_SOUMISSION.md`. |
| The split or the VPS tests are still red on Sunday night | Finish on Monday 19 or Tuesday 20, still before 22 October 00:00 UTC. The old VPS directory stays until §6 is green. If the split still is not pushed when the GenAI hackathon opens: an `agent-poe` branch in the old repository, created after 00:00 UTC, declared in the README. |

## 6. Point the VPS at the new repos, then archive

Today one directory serves both products: `~/blue-intelligence-map` (`/home/ubuntu/blue-intelligence-map`). systemd units hard-code it (`blue-intelligence.service`, `naviguide-simulator.service`, `naviguide-api.service`, `naviguide-polar.service`, `naviguide-orchestrator.service`). `deploy-app.sh` sets `APP="$HOME/blue-intelligence-map"`. GitHub Actions in the mono-repo copies that directory over SSH.

Over the weekend the VPS moves to two directories:

| New directory | Repository | Replaces |
|---|---|---|
| `~/blue-intelligence` | Blue Intelligence | `backend/`, `frontend/`, product `infra/vps/` |
| `~/naviguide` | NAVIGUIDE | `naviguide-simulator/`, `naviguide/`, `infra/vps/naviguide/` |

`.service` files and deploy scripts are updated to these paths, in the repository that owns them, the same weekend. Those are split commits, before 22 October. VPS secrets (`~/.config/blue-intelligence/`, `backend/.env`, `~/.config/naviguide/simulator.env`, the deploy SSH key) stay on the machine: they are not in git. GitHub Actions secrets (`VPS_SSH_KEY`, `VPS_HOST`) are copied onto both new repositories. The mono-repo deploy workflow is disabled before the first new deploy, so a push to `Blue-Intelligence-Map` cannot overwrite the new directories.

Mongo does not move. Same `mongod`, same data. During these deploys: do not run `sync-from-atlas.sh`, and do not write to `poe_ports` or the runs. Count `poe_ports` before and after: the number must match.

The old directory `~/blue-intelligence-map` stays on disk until the tests finish. If a test fails, point the services back at that directory. Archive nothing yet.

Checklist that makes it reasonable to archive `Blue-Intelligence-Map`:

1. `GET http://127.0.0.1:8001/api/` on the VPS returns 200, as at the end of `deploy-app.sh`.
2. `https://blueintelligence.online/api/` returns 200.
3. `https://www.naviguide.fr` returns 200.
4. `https://simulator.naviguide.fr` returns 200.
5. The simulator still reads Blue Intelligence: a layer that goes through `BI_API_URL` (ports, PoE, or MPA) renders, and the proxy returns no error.
6. `systemctl is-active` is `active` for `blue-intelligence`, the simulator, and the NAVIGUIDE services that were running before.
7. The `poe_ports` count is identical before and after.
8. A deploy starts from each new repository and does not read `Blue-Intelligence-Map`. A push to the mono-repo no longer deploys.

While any line is red, the mono-repo stays the reference and is not archived. When all eight are green, no service needs it: archiving is then possible. Do it at that moment.

---

## Decisions

| # | Topic | Decision |
|---|---|---|
| 1 | Two repositories | Weekend of 17–18 October 2026: two new repositories, **NAVIGUIDE** and **Blue Intelligence**, and the VPS pointed at them (§6). `Blue-Intelligence-Map` may be archived only when the eight tests are green. No agent code this weekend. |
| 12 | Fallback branch | The split is the weekend of 17–18 October. If it is still not pushed at 22 October 00:00 UTC: a branch in the old repository, created after that time, declared in the GenAI hackathon README. |
