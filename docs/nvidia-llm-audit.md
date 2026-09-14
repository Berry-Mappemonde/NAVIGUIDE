# NIM fallbacks by usage — verdict and plan

Provider (price, unchanged): **the whole NIM chain for the role**, then OpenRouter, then Claude.
This document only covers the order of **NVIDIA models inside NIM**.

**Canary:** 2026-09-09 08:08 UTC, `backend/scripts/probe_nvidia_usages.py`.
**Single source in the code:** `CHAINS` in `backend/app/core/nvidia.py`. `models_for(role)` no longer reorders Muse into 2nd.

---

## 1. Verdict

Five hosted ids hold a PoE / page JSON. A single model is not enough (410, 429, 503, 529, timeout).

| id | Role in NIM |
|---|---|
| `deepseek-ai/deepseek-v4-pro-0813` | Head of every chain except `legal` |
| `openai/gpt-oss-20b` | 2nd (equal quality, faster than Muse under load) |
| `meta/muse-glimmer-30b` | 3rd (4/4, no `json_object`, slow under load) |
| `deepseek-ai/deepseek-v4-flash-0731` | Last of the **judge only** (frequent 529) |
| `moonshotai/kimi-k3` | Head of **`legal` only** (timeout / 429 on the daily judge) |

Outside `CHAINS`: Laguna (503), MiniMax (429 + licence), Lightning (false Tiwai), Gemma 4 (hang), Llama 3.2 11B (TW 500, marina without JSON).

Historical pin removed: Muse is no longer “the harbour-master model” nor the implicit 2nd of `models_for`. Harbour masters = the same `page` chain as marinas.

---

## 2. Implementation plan — one NIM chain per usage

Execution rule in `_complete_one` / `complete_json_nvidia_tracked`:

- 410 / 404 → **immediate** next model
- 429 / 503 → retry then next
- 529 → next (Flash, not on the retry list)
- 120 s timeout → next (do not 3×120 s)

Operator override: `NVIDIA_MODEL_CHAIN_{ROLE}` (full list). `NVIDIA_MODEL` only
**prefixes** if set; it does not overwrite the rest of the chain.

### Table

| Usage | `role` | NIM chain | Call site | Why this order |
|---|---|---|---|---|
| PoE judge (seed) | `judge` | **Pro → gpt-oss → Muse → Flash** | `poe_seed_enrich._judge_llm` | Pro 4/4 ~5 s conf 100. gpt-oss 4/4 ~10 s. Muse 4/4 but 57 s under load. Flash last: 529 on Fort Bay. Listing = hop to the **next of this list**, no longer to Muse by name. |
| Extract port lists | `extract` | **Pro → gpt-oss → Muse** | `extract_ports_nvidia`; 2nd reader = 1st id ≠ head | Pro 5/5 in 6 s, gpt-oss 8 s, Muse 102 s under load. Kimi **removed** from this chain (429). |
| Decree / gazette | `legal` | **Kimi → Pro → Muse** | `second_extract_choice` if `looks_like_legal_text` | Thinking always on, extract of an order OK outside 429. Not a daily judge. |
| Generic JSON | `json` | **Pro → gpt-oss → Muse** | gatekeeper, `extract_project`, `llm_geocode`, AMP `llm_judge_visit`, `arbitrate_geocode` | Same ranking as the judge **without** Flash (529 too expensive at the head of the JSON queue). |
| Marina **and** harbour-master page | `page` | **Pro → gpt-oss → Muse** | `marina_enrich.enrich_via_nvidia`, `capitainerie_enrich.enrich_via_nvidia` | Marina canary: Pro 2.3 s 4/4; gpt-oss 14 s; Muse 19 s. Flash 8 s but 529 elsewhere → not 2nd on page. **One chain** for both modes. |
| Free text | `text` | **Pro → gpt-oss → Muse** | `ask_text` / `complete_text_nvidia` (`json_object=false`) | Same order; Muse no longer at the head (no text-only canary that would justify it). |
| Web search | — | **no NIM** | `grounded_search` | No `:online` plugin on `integrate.api.nvidia.com`. |

After the “NIM chain” column is exhausted: OpenRouter, then Claude (except marinas / harbour masters / `ask_text` / web — see existing contracts).

### Second extract reader

No longer “Muse in parallel by inheritance.” It is the 2nd id of the role’s chain:

- non-legal page → **gpt-oss**
- `looks_like_legal_text` → **Kimi** (`legal` chain)

### Harbour masters

No dedicated model. TinyFish regex first (phone + VHF → stop). Otherwise `role="page"` without `model=`. The persisted label is `engine_label(served model)` (`nvidia-deepseek` if Pro answers).

---

## 3. Canary evidence (08:08 UTC)

| id | FB | TW | Extract | Marina |
|---|---|---|---|---|
| Pro-0813 | 4.78 s accepted/100 | 1.01 s cargo/95 | 5.97 s 5/5 | 2.32 s 4/4 |
| gpt-oss-20b | 10.0 s accepted/80 | 7.33 s cargo/80 | 8.14 s 5/5 | 14.0 s 4/4 |
| Muse | 56.6 s accepted/95 | 50.9 s cargo/95 | 101.7 s 5/5 | 19.1 s 4/4 |
| Flash-0731 | **529** | 6.99 s OK | 11.7 s 5/5 | 8.24 s 4/4 |
| Kimi-K3 | timeout 120 s | 429 | 429 | 429 |
| Llama 3.2 11B | 9.1 s OK | **500** | 28 s 5/5 | 200 without JSON |
| Laguna 2.1 | 503 | 503 | 503 | 503 |

Flash **can** extract and read a page; the 529 is trial load, not incompetence. Hence the queue, not the head.

Muse 4/4 when idle (~1 s the day before) and 57 s the next day, same payload. Hence 3rd, not 2nd.

---

## 4. Parameters (infer sheet, not the playground)

| Model | Payload |
|---|---|
| Pro | effort `none`; `{thinking:false}`; temp **0 only**; `json_object` |
| Flash | effort **`none` forced** (infer default = high); `json_object` |
| gpt-oss | 0.6 / 0.7; effort `low` (default medium; no `none`); `json_object` |
| Muse | 0.95 / 1.0; effort `low`; **no** `json_object` |
| Kimi | temp 1.0; **no top_p**; effort `low` / `high` if `role=legal`; `json_object` |

---

## 5. Done / not done

**Done:** `CHAINS` = §2 table; `models_for` no longer prefixes Muse; judge / extract / json / page / text aligned; harbour masters on `page`; Kimi out of daily extract.

**Not NIM:** `grounded_search` (`:online`). Marinas / harbour masters without Claude. Self-host NIM out of scope.

**Replay:** `backend/scripts/probe_nvidia_usages.py` if NVIDIA EOLs an id (dated successor).
