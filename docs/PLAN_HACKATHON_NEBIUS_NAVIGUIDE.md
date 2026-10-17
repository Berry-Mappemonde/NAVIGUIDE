# Nebius × NVIDIA hackathon plan — NAVIGUIDE

Plan date: 17 October 2026. Entry point for the **Nebius × NVIDIA Global AI Hackathon** (Devpost). The submitted product is **NAVIGUIDE**. Blue Intelligence stays an HTTP source; its own hackathon is [PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md](PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md).

The repository split, the same weekend, is in [PLAN_SEPARATION_DEPOTS.md](PLAN_SEPARATION_DEPOTS.md). As soon as the NAVIGUIDE repository exists, the Devpost form cites that URL.

Working documents stay beside this plan, each with its own job:

| Document | Role |
|---|---|
| [HACKATHON_DEVPOST_SOUMISSION.md](HACKATHON_DEVPOST_SOUMISSION.md) | English text to paste, form fields, video shot list |
| [PLAN_NEMOTRON_NEBIUS_TAVILY.md](PLAN_NEMOTRON_NEBIUS_TAVILY.md) | Cascade, prices, guards, lots L1–L6 (20 September) |
| [PLAN_BATCH_2026-10-16.md](PLAN_BATCH_2026-10-16.md) | Lots still to build so the Nebius call is visible (16 October) |
| `infra/agents/GROK_BOT_DEVPOST.md` | Bot routine: read the form, fill the draft, film. The owner submits. Exchange point: issue #432 |

---

## 1. Product

**NAVIGUIDE** (`naviguide-simulator/`, live at `https://simulator.naviguide.fr`): the boat glides along the route, rules decide *when* to speak, sources decide *what is true*, and Nemotron on Nebius Token Factory decides *how to say it*. A number on screen comes from a calculation or a source. A server-side filter rejects any figure the model did not receive.

Blue Intelligence (`https://blueintelligence.online`) is the memory (ports of entry, marinas, harbour masters, marine protected areas). The simulator calls it through `BI_API_URL`. The Nebius jury grades the briefing, not the PoE agent.

Proposed form name (≤ 60 characters): `NAVIGUIDE — a sailor's briefing that glides`. Pitch and “About”: paste them from `HACKATHON_DEVPOST_SOUMISSION.md` § 1 and § 2, updated for what changed after 20 September (two modes **Follow / Draw**, anchored film, `on-demand` mode).

## 2. Eliminatory rule

The project makes a **runtime call** to the **Nebius Token Factory** inference API, with **at least one NVIDIA open-source model**.

- Base URL: `https://api.tokenfactory.nebius.com/v1` (OpenAI-compatible), key `NEBIUS_API_KEY`.
- NIM (`https://integrate.api.nvidia.com`) does not satisfy this rule. The submission cascade calls Token Factory first.
- The call is **visible**: the label under the generated text names the model and “Token Factory”.
- The call leaves **the server**, on a user gesture (the **Written** pill, a chat question, a harbour questionnaire). Background warm-up does not call a model.

Form track: **Best apps and agents**. The project **existed** before 26 August 2026 and has been heavily rebuilt since. Measure the code share with `python3 infra/agents/devpost_code_share.py`. Do not reuse the 29 September figure.

## 3. Calendar

Taken on 14 October (`PLAN_BATCH_2026-10-14.md` § 4, owner review). Judges test from **1 to 15 December**: Token Factory credits must still be valid on that date.

| When | What |
|---|---|
| Weekend of 17–18 October | Repository split ([PLAN_SEPARATION_DEPOTS.md](PLAN_SEPARATION_DEPOTS.md)). Public YouTube video, under 3 minutes, shot from the **2:30** pill in English. Re-read the Devpost draft. The owner clicks **Submit**. |
| Friday 23 October | Submission update. |
| **30 October, 10:00 PT** | Final submission. |
| 1–15 December | Window in which judges re-run the demo. |

The bot does not click Submit. Chain: scrape the form (issue #432) → proposed answers from `HACKATHON_DEVPOST_SOUMISSION.md` → draft filled → the owner submits.

Credits: the trial opened on 13 September (29 days) fell due around **12 October**. The Devpost form and the Nebius Builders Program each add **+$25** (Resources page). Before sending, open the Nebius console and check that the balance covers the judges’ window. The repository contains no amount and no key.

## 4. Model contract — what the judges see

Decisions of 14 October (owner review) and 16 October (batch 3). Since 29 September the mode is `on-demand`: the Ultra judge and the background Tavily watch are off. Chat is the live use. The **Written** pill has to become the most visible Nebius call again.

| Gesture | Model | Lot | What the screen shows |
|---|---|---|---|
| Click **Written** (`Rédigé`) | Super writes the French from the facts; Ultra edits; Ultra judges in a **separate** call; Lightning translates | **ED1** (takes over **RG11**) | The wording changes. Label “Nemotron 3 Super · Token Factory”. Fall back to the rules text if a number, a name, or a date moves. One generation per day and per variant, served from the store. Opening Follow spends nothing. |
| Simple chat question | Rules, or Lightning when it is on | **CH1** | Answer taken from the journal. |
| Hard chat question | Ultra, when it is on and under the cap; otherwise the rules | **CH1** | No “Reasoning” checkbox. |
| Harbour questionnaire | Tavily, two rounds, on a list that is already written | **TV1** | One dated sentence and one address, in the harbour sheet or the chat. In the film only if **VS1** kept that id. |
| Spend brake | Counters already on `GET /ici/warm/status` | **NB1** | Nothing on screen. Missing `NAVIGUIDE_LLM_DAILY_USD` means no dollar cutoff while usage is being measured. The judge tier stays at **0** in the repository. |

Lot agents run with `NAVIGUIDE_LLM_MODE=off`. Tests simulate Lightning, Super, Ultra, VL, and Tavily. No Nebius call during a lot.

The September price grid (Lightning $0.06 / $0.24, Super $0.30 / $0.90, Ultra $1 / $3 per million tokens) and the anti-loop guards stay in `PLAN_NEMOTRON_NEBIUS_TAVILY.md`. The October batch tightens *where* calls happen: the film on click, chat on a question, Tavily on the harbour questionnaire. Nightly story pre-generation and the background truth judge stay off.

**Did you use Tavily?** Check **Yes** only if TV1 (or the L3 judge) is actually running in production at submit time. Otherwise **No**. Do not check a use that is switched off.

## 5. Video

Public YouTube, under 3 minutes, target 2:30, no copyrighted music. Source: the film’s **2:30** pill (lot **RC27**: the compact template fits in 150 seconds). The app is in English in the video. The minute-by-minute shot list is in `HACKATHON_DEVPOST_SOUMISSION.md` § 2. Recut it to what is true on shoot day: Follow, the film, the Token Factory label under **Written**, a chat question whose number comes from the journal, Draw.

The video file does not go into git. The form receives the YouTube link.

## 6. Checklist before Submit

- [ ] `https://simulator.naviguide.fr` responds, and a **Written** click shows the Token Factory label (ED1 / RG11 in production, `NEBIUS_API_KEY` on the VPS, `on-demand` mode).
- [ ] The 2:30 pill lasts 2:30 (RC27).
- [ ] English README of the submitted repository: install, run, section “How we use Nemotron on Token Factory”.
- [ ] MIT licence visible. Repository URL = the **NAVIGUIDE** repository once the split is green; until then the current public repository, and update the URL as soon as the new repository is pushed.
- [ ] Public YouTube video, link pasted.
- [ ] English text from `HACKATHON_DEVPOST_SOUMISSION.md`, figure regenerated by `devpost_code_share.py`, scores 1–10 filled after real use (do not invent the score).
- [ ] Token Factory balance still valid on 15 December.
- [ ] Tavily checkbox matches what is actually running.
- [ ] The owner clicks Submit. The bot stops at the draft.

## 7. Outside this submission

- The PoE agent, Zetaris, Toloka, Nemotron VL on official PDFs: GenAI.works hackathon, Blue Intelligence repository.
- VL around the boat, voice input, LangSmith, Ultra as the film’s author, story pre-generation: outside the 16 October batch.
- A number produced by a model, a key in the README, a push that rewrites Mongo.
