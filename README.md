[Français](README.fr.md)

# NAVIGUIDE

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE-MIT)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE-APACHE)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron-76B900.svg)](https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/)
[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token%20Factory-0B1F3A.svg)](https://tokenfactory.nebius.com/)

NAVIGUIDE is the expedition cockpit for the Berry-Mappemonde voyage: a map, the boat, and a briefing written only from structured facts, with NVIDIA Nemotron on Nebius Token Factory.

**Live: https://naviguide.fr**

**Demo video:** https://youtu.be/pH5ZtAh_NQA

> **Not for navigation.** Maps and figures come from public sources and calculations. This is not an official chart. Check government publications before any decision at sea.

## What it is, and who it is for

NAVIGUIDE follows the Berry-Mappemonde expedition on a map and briefs the harbour ahead from structured facts: maritime borders, ports, protected areas, wind and sea state.
It is for the crew and for anyone watching that voyage. The locked official departure is 15 May 2026, 08:00 UTC.
It is also for judges of the Nebius × NVIDIA hackathon who want to see Nemotron answer on Token Factory from those facts, not from an open-ended chat.
A missing fact stays empty. A figure is shown only when a measurement or a published source already contains it.
It is not an official chart, and it is not for decisions at sea.

Manuals: [English](docs/USER_MANUAL.md), [French](docs/MANUEL_UTILISATEUR.md).

## Try it in 60 seconds

On [https://naviguide.fr](https://naviguide.fr). The first visit opens in English. If the follow button is not in English, click **EN**.

Shortcut: [https://naviguide.fr/?tour=1](https://naviguide.fr/?tour=1) opens the judges’ guided tour on load (the **Guided tour** button opens it too). Its second step, **Who does what: Nemotron and Tavily**, names the model behind each job, read live from `GET /ici/warm/status` (or the code defaults, marked as such), plus today’s Nemotron calls and Tavily searches on the server.

1. Click **Follow expedition**.
2. Click **Replay the expedition**. If it is grey, the tooltip says **preparing**.
3. When the film controls are up, **Raw** and **Edited** sit side by side. **Edited** is the written narration. If **Edited** is grey, the tooltip says **not yet written for this duration**. For accessibility, the speaker button in the film bar (labelled **Listen**) reads the film aloud: during a replay, the browser’s own speech synthesis (`speechSynthesis`, `naviguide-simulator/src/utils/speak.js`) reads each paragraph as the film plays, in English or French, with no Nemotron call and no NAVIGUIDE server call.
4. When the boat is at a stop, the panel is titled **Port of call sheet**. If that stop is inside the watch window and a watch was stored, a card is titled with the port name, the words **watch of**, and a date, plus one sentence. If no watch was stored, that card is absent. The sheet still lists the places it has.
5. In the side panel, **Logbook — ask a question**. The field reads **Wind at the boat? Next stop?** Press the button whose tooltip is **Send**. Under **Try a question:**, three chips send a ready question in one click: **Why? · Ultra** (a why question, answered by Nemotron 3 Ultra), **Port news · Tavily** (how the web describes the port of the next stop: Ultra with Tavily web sources) and **Wind · Lightning** (Lightning reads the question, the facts answer).

A plain logbook question is answered from the facts already collected. A why, a how, or a long question is the one sent to Nemotron 3 Ultra when the budget allows. The chat then shows: **You are interacting with artificial intelligence. Replies are generated automatically and may contain errors.**

## How we use NVIDIA Nemotron on Nebius Token Factory

Primary inference goes to Nebius Token Factory. The ids below are the defaults in `naviguide-simulator/server/llm_budget.py`. An environment variable `NAVIGUIDE_TF_MODEL_*` can replace one of them.

| Gesture | Tier | Model | File |
|---|---|---|---|
| Logbook question, JSON only | `nano` | `nvidia/Nemotron-3_5-Lightning` | `naviguide-simulator/server/logbook_chat.py` |
| Film moment ids | `nano` | `nvidia/Nemotron-3_5-Lightning` | `naviguide-simulator/server/film_script.py` |
| Second watch question, one id from a fixed list | `nano` | `nvidia/Nemotron-3_5-Lightning` | `naviguide-simulator/server/escale_watch.py` |
| Short sentences, and French to English | `fast` | `nvidia/Nemotron-3_5-Lightning` | `naviguide-simulator/server/story_cascade.py` |
| Port-of-call paragraph | `fast` | `nvidia/Nemotron-3_5-Lightning` | `naviguide-simulator/server/escale_api.py` |
| One-sentence watch summary | `fast` | `nvidia/Nemotron-3_5-Lightning` | `naviguide-simulator/server/escale_watch.py` |
| “Here” card when a written story is asked | `write` | `nvidia/Nemotron-3.5-Super-VL` | `naviguide-simulator/server/story_cache.py` |
| Written story of a stopover or a major alert (gale, cyclone, depth alert, refuge marina, any `alert` severity) | `deep` | `nvidia/Nemotron-3-Ultra-550b-a55b` | `naviguide-simulator/server/story_cascade.py` |
| Written film chapters | `write` | `nvidia/Nemotron-3.5-Super-VL` | `naviguide-simulator/server/film_script.py` |
| Plan-review comment | `write` | `nvidia/Nemotron-3.5-Super-VL` | `naviguide-simulator/server/plan_review.py` |
| Edit, then judge, the written film | `judge` | `nvidia/Nemotron-3-Ultra-550b-a55b` | `naviguide-simulator/server/film_script.py` |
| Hard logbook question | `judge` | `nvidia/Nemotron-3-Ultra-550b-a55b` | `naviguide-simulator/server/logbook_chat.py` |
| Stale official-port claim, only if that judge is switched on | `judge` | `nvidia/Nemotron-3-Ultra-550b-a55b` | `naviguide-simulator/server/truth_judge.py` |
| Look at a local drawing of the route (not the Draw button’s routing) | — | `nvidia/Nemotron-3.5-Super-VL` | `naviguide-simulator/server/vl_route.py` |

The `deep` tier uses the same Ultra id. `story_tier` in `naviguide-simulator/server/story_cascade.py` picks it for the written story (`POST /ici/story`) of a stopover or a major alert; every other written story stays on `write`. The VL call runs only from `naviguide-simulator/scripts/one_shot.py` with `--run`. The image it sends is drawn locally. Map tiles are not sent.

Nemotron 3 Nano 30B and Nemotron 3 Super 120B leave Token Factory on 9 November 2026, so the `nano` tier now serves Lightning and the `write` tier serves Super VL. Both ids are listed by `GET /v1/models` on Token Factory. Hosts in `naviguide-simulator/server/story_cascade.py`: the `nano` tier on `https://api.tokenfactory.nebius.com/v1` (EU base), Lightning (`fast`) and Super VL (`write`) on the same default base (`NAVIGUIDE_TF_BASE` changes it), Ultra (`deep` and `judge`) on `https://api.tokenfactory.nebius.com/v1` (EU base).

**Cascade.** A 24-hour SQLite cache is read first. If the daily budget or `NAVIGUIDE_LLM_MODE` refuses the call, nothing is sent and the source is `budget`. Otherwise the default order in `DEFAULT_PROVIDERS` is Token Factory, then NIM, then OpenRouter, then Claude. If the caller passed a fallback string and every provider failed, the source is `rules`.

On the `fast` tier only, an empty Token Factory body, an HTTP status of 500 or higher, or a timeout is tried once more on Token Factory with the Super VL model. A 4xx does not take that second try. On the `nano` tier, a Token Factory failure is tried once more on Token Factory as Lightning, then the cascade continues. NIM is `openai/gpt-oss-20b` at `https://integrate.api.nvidia.com/v1/chat/completions`. OpenRouter defaults to `openai/gpt-4o-mini`. Claude is `claude-haiku-4-5`.

**Numbers.** `filter_numbers` in `naviguide-simulator/server/story_cascade.py` drops every sentence that contains a number not already in the facts. A sentence with no number is kept. The filter does not catch a non-numeric invention.

**Budgets** when the matching variable is unset (`naviguide-simulator/server/llm_budget.py`):

| Tier | Tokens per day |
|---|---|
| `nano` | 100,000 |
| `fast` | 200,000 |
| `write` | 450,000 |
| `deep` | 150,000 |
| `judge` | 250,000 |

The written film’s edit and re-read go to Ultra by default, inside that `judge` budget (`film_ultra_open` in `naviguide-simulator/server/film_script.py`). Setting `NAVIGUIDE_LLM_DAILY_TOKENS_JUDGE` to `0`, a negative or a non-numeric value switches Ultra off for the film, which then falls back to Super VL. Hard logbook questions are bounded by the same `judge` budget. A separate 10-per-day Ultra chat counter (`allow_chat_ultra` in `naviguide-simulator/server/llm_budget.py`) is reported in the budget status but is not checked before a logbook answer on this commit. There is no dollar cutoff unless `NAVIGUIDE_LLM_DAILY_USD` is set. The commented figures in `naviguide-simulator/server/.env.example` are not these defaults. Default mode is `on-demand` (a user action, not a background job). `off` never pays. `all` is explicit.

**Public proof.** `GET /ici/warm/status` includes `llm`, and `llm.lastSourceByTier` when a tier has already answered. The value is the source that answered (`nemotron-lightning`, `nemotron-super-vl`, `nemotron-ultra`, or a fallback name), not a sentence from the model.

On screen, a Token Factory answer is named in text, for example **Nemotron 3.5 Lightning · Token Factory**. The film bar keeps one short line, **Models**, naming the model that answered. A fallback stays labelled **NVIDIA NIM (fallback)**, **OpenRouter**, **Claude**, or **rules**. There is no third-party logo.

## Tavily

Tavily is called at runtime in three places a visitor reaches: the logbook chat, the **Port news · Tavily** chip (the same chat path), and the **Edited** film.

**Logbook chat.** Each question sent with the **Send** button of “Logbook — ask a question” runs one Tavily search (`naviguide-simulator/server/port_web_context.py`) about a port: the port nearest the film boat, or the next official stop when you follow the live boat. It is on by default (`NAVIGUIDE_PORT_WEB=0` turns it off), cached per query and per day, and counted in the 80 daily Tavily credits. The links are listed under **Web sources (Tavily)** below the answer. A hard question sends the extracts to Ultra, which must attribute them (“according to a web source”) and never mix them with the boat’s figures. The **Port news · Tavily** chip sends a “how” question, so its answer goes to Ultra with those extracts.

**Edited film.** Clicking **Edited** (`POST /voyage/official/film`) runs one Tavily search on the last port the film reaches (`naviguide-simulator/server/film_web_context.py`), through the same cache and the same daily credit cap. Only titles and links are kept, at most three, and no extract is copied into the film text. They show under the film bar as **Web sources (Tavily) · {port}:**. With no key, no credit left or no result, nothing is shown.

The stop watch below is a separate server job.

The watch is a server job. It stays off until `NAVIGUIDE_TAVILY_WATCH=1` (the default is `0`). When it is on, it covers a stop from 10 days before arrival through 2 days after, at most two rounds, once per stop. Lightning writes one sentence from the extracts. If a second round is needed, the `nano` tier (Lightning) picks one remaining id from a fixed list. It does not invent a question. Caps, unless overridden: 2 searches per stop, 6 searches per day, 80 Tavily credits per day. The dated card, when a watch is stored and not expired, is titled `{name} · watch of {date}`.

The separate “re-read the official port page” judge is off unless `NAVIGUIDE_TRUTH_JUDGE=1`.

## Where Nebius Token Factory accelerated us

- **Drop-in provider.** Token Factory speaks the OpenAI chat-completions format, so adding it as the first provider of our existing cascade took one commit (`b8e294d`, September 20, 2026), four days after the cascade itself was wired (`a60f53e`, September 16).
- **One table, one place to pick a model per job.** Tiers in `naviguide-simulator/server/llm_budget.py` map each job to a Nemotron size. Moving short JSON calls to Nano (`d665fff`) and short sentences to Lightning (`18ba74a`) changed that table plus the call sites, labels and tests, while every fallback was kept.
- **A writer and an editor from the same provider.** By default, Super VL writes the film chapters and Ultra edits and judges them, so the quality loop runs inside one API and one bill.

Other Nebius services: none beyond Token Factory.

## Architecture and data sources

```
naviguide.fr  →  nginx  →  naviguide-simulator
                            ├── Vite / React (dist/)
                            └── FastAPI (uvicorn :8010)
```

The simulator does not run MongoDB. Blue Intelligence is a separate HTTP API. The partial `backend/` tree in this repository is not that API.

Licences are stated here only when this repository names them. The sheet with URL, on-screen credit, and survey date is [naviguide-simulator/DATA_SOURCES.md](naviguide-simulator/DATA_SOURCES.md).

| Source | Licence written in this repository |
|---|---|
| Marine Regions EEZ v12 | CC-BY 4.0. This repository does not contain CC-BY-NC-SA and does not settle that difference. |
| OpenStreetMap | ODbL is named for the OpenSeaMap seamarks. The base map credits OpenStreetMap contributors. |
| EMODnet | CC-BY 4.0 |
| World Port Index, Copernicus Marine, GEBCO, ProtectedSeas / MPAs, Saildocs / GRIB, Tavily, Blue Intelligence | Not named next to those sources. See the data sheet. |

Model governance: [naviguide-simulator/docs/AI_GOVERNANCE.md](naviguide-simulator/docs/AI_GOVERNANCE.md).

## Run locally

| Tool | Version |
|---|---|
| Node.js | 24 ([.nvmrc](.nvmrc)) |
| Python | 3.12 (as in [.github/workflows/ci.yml](.github/workflows/ci.yml)) |

From a clean clone:

```bash
git clone https://github.com/Berry-Mappemonde/NAVIGUIDE.git
cd NAVIGUIDE/naviguide-simulator
```

On macOS, `./dev-mac.sh` creates `.venv` and installs npm packages the first time those folders are missing, then serves the API on port 8010 and the UI on port 5174.

Or install and start the two processes yourself:

```bash
npm ci
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --port 8010
npm run dev
```

`npm run dev` is the Vite dev server. `npm run server` is the same API with `--reload` on `127.0.0.1:8010`.

Names in [naviguide-simulator/server/.env.example](naviguide-simulator/server/.env.example), and nowhere a value: `NEBIUS_API_KEY`, `NAVIGUIDE_TF_BASE`, `NAVIGUIDE_TF_MODEL_NANO`, `NAVIGUIDE_TF_MODEL_FAST`, `NAVIGUIDE_TF_MODEL_WRITE`, `NAVIGUIDE_TF_MODEL_JUDGE`, `NAVIGUIDE_LLM_PROVIDERS`, `NAVIGUIDE_LLM_DAILY_TOKENS_NANO`, `NAVIGUIDE_LLM_DAILY_TOKENS_FAST`, `NAVIGUIDE_LLM_DAILY_TOKENS_WRITE`, `NAVIGUIDE_LLM_DAILY_TOKENS_JUDGE`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `NVIDIA_API_KEY`, `TAVILY_API_KEY`, `TAVILY_API_BASE`, `NAVIGUIDE_TAVILY_WATCH`, `NAVIGUIDE_WATCH_DAILY_SEARCHES`.

`NAVIGUIDE_LLM_MODE` is read by the server and is not in that example. Set `NAVIGUIDE_LLM_MODE=off` to run with no paid model call. Stories then stay on rules, cache, or the local text.

Python packages are pinned in [naviguide-simulator/server/requirements.txt](naviguide-simulator/server/requirements.txt).

## Tests

From `naviguide-simulator/`:

```bash
npm test
python -m pytest -q
npx playwright test
```

CI runs the same Node tests, the Vite build, and pytest when `naviguide-simulator/` changes, then Playwright. See [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Deploy

A merge to `main` deploys [https://naviguide.fr](https://naviguide.fr) on Contabo. The workflow is [.github/workflows/deploy.yml](.github/workflows/deploy.yml).

## Changes since August 26, 2026

Measured from git on code files only. The sentence is copied from that measurement. It is not an estimate.

In numbers (from git, code files only): on August 26, 2026 the repository held 0 code files and 0 lines — the NAVIGUIDE simulator did not exist. Today it holds 708 code files and 174,566 lines, and 100% of those lines (174,566) were written or rewritten since August 26, 2026 — 1094 commits, 811 files touched. The simulator (171,071 lines) is entirely post-August 26, 2026.

## Known limitations

- **Fallbacks are not NVIDIA-on-Nebius.** When Token Factory fails, the default order continues to NVIDIA NIM (`openai/gpt-oss-20b`), then OpenRouter (`openai/gpt-4o-mini`), then Claude (`claude-haiku-4-5`). Such answers are labelled with their provider, not as Nemotron.
- **The number filter only checks numbers.** `filter_numbers` drops a sentence whose figures are not in the facts. A sentence with no number is kept, so a non-numeric invention is not caught.
- **The official-port judge is off by default.** It runs only when `NAVIGUIDE_TRUTH_JUDGE=1`.
- **No dollar cap by default.** Daily token budgets apply per tier, but there is no dollar cutoff unless `NAVIGUIDE_LLM_DAILY_USD` is set.
- **Cached answers can be up to a day old.** The cascade cache lives 24 hours; a written film is cached for one day, a written story for seven days.
- **Edited is not always available.** If no written film exists for the chosen duration, the **Edited** button is grey.
- **No red-team evaluation.** This repository has no red-team eval directory or report, and was not adversarially tested with NVIDIA garak or promptfoo.
- **Not for navigation.** Maps and figures come from public sources and calculations; this is not an official chart.

## Responsible AI and security

Generated text is marked. The label is **AI-generated content (model: {model})**. The same block sets `data-ai-generated`. The server payload can carry `ai_generated` and `generated_at` (`naviguide-simulator/server/ai_transparency.py`). The chat notice is the sentence quoted in the 60-second path. That is the marking this repository ships for AI Act article 50. Whether the product is high-risk, and how the two paragraphs of article 50 attach, is not settled in the tree: see [naviguide-simulator/docs/AI_GOVERNANCE.md](naviguide-simulator/docs/AI_GOVERNANCE.md). This repository contains no watermark string.

This checkout does not contain a red-team eval directory or a red-team report. This README does not say the product was adversarially tested with NVIDIA garak or promptfoo.

Policy: [SECURITY.md](SECURITY.md). Data sheet: [naviguide-simulator/DATA_SOURCES.md](naviguide-simulator/DATA_SOURCES.md).

[![CodeQL](https://github.com/Berry-Mappemonde/NAVIGUIDE/actions/workflows/codeql.yml/badge.svg)](https://github.com/Berry-Mappemonde/NAVIGUIDE/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/Berry-Mappemonde/NAVIGUIDE/badge)](https://scorecard.dev/viewer/?uri=github.com/Berry-Mappemonde/NAVIGUIDE)

The badges point at [.github/workflows/codeql.yml](.github/workflows/codeql.yml) and [.github/workflows/scorecard.yml](.github/workflows/scorecard.yml). CodeQL is not a required check. [SECURITY.md](SECURITY.md) records that, as of 18 October 2026, this repository had no published CodeQL result yet.

## License

Code is [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE), at your option. Data keeps the licence named above, or the one in the data sheet. Nemotron weights are not in this repository. They are served by Token Factory and NIM under the [NVIDIA Nemotron Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/).
