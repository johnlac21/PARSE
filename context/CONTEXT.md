# PARSE — Context for LLMs

**Use this file (and optionally the READMEs below) when giving an LLM project context.** It summarizes goal, scope, repo structure, and where to find details.

---

## Goal & scope (one paragraph)

**PARSE** (Prompt Alteration Response-Shift Evaluation) is a full-stack app that (1) lets you upload baseline prompts (CSV/JSONL), (2) generates linguistic variants (grammar from 189 Ziems Multi-Value paper features, typos, dialect/language via LLM rewriting), (3) runs those prompts against one or more LLMs, and (4) analyzes how responses *shift*—difference (LPM), directional bias, completeness—with export to LaTeX/CSV/JSON and interactive charts. The goal is to evaluate how robust or biased model behavior is under prompt variation (dialect, typos, grammar).

---

## Repo structure (project-owned only)

```
PARSE/
├── README.md                 # Overview, quick start, architecture, grammar/typo tables, citation
├── context/
│   └── CONTEXT.md            # This file
├── docker-compose.yml        # backend:8000, frontend:3000
├── backend/
│   ├── README.md             # API endpoints, how to add grammar features, how to add parsers
│   ├── main.py               # FastAPI app, CORS, routers, startup
│   ├── db.py                 # SQLAlchemy: Project, Prompt, Run, Result, UploadStaging
│   ├── requirements.txt
│   ├── models/
│   │   └── schemas.py        # Pydantic request/response models
│   ├── routers/
│   │   ├── projects.py      # CRUD, upload CSV/JSONL, map columns, list prompts
│   │   ├── variants.py      # grammar/typo features, preview, applicability, generate
│   │   ├── runs.py          # create run, progress, SSE stream, cancel, list by project
│   │   ├── analysis.py     # difference, directional-bias, completeness, export, raw results
│   │   └── dialect.py       # available dialects, test connection, rewrite preview, generate
│   ├── engine/
│   │   ├── grammar/         # registry, transforms (189 paper features; all have real transforms), applicability
│   │   ├── typos/           # registry, transforms (6 types)
│   │   ├── combinator.py    # generate grammar/typo/all variants
│   │   └── dialect/         # config (AAVE, Gen Z, etc.), LLM rewriter
│   ├── llm/
│   │   ├── providers.py     # LiteLLM client
│   │   ├── runner.py        # async run over prompts, rate-limit backoff, parsers
│   │   └── parsers.py       # Likert, recommendation_list, free_text → get_parser(modality)
│   ├── analysis/            # difference (LPM), directional_bias, completeness, export (latex/csv/json)
│   ├── utils/               # errors, startup (load grammar/typo)
│   └── shared/              # optional grammar_features.json (see also project root shared/)
└── frontend/
    ├── README.md             # Component structure, how to add analysis views
    ├── src/
    │   ├── app/              # App Router: page, project/[id], configure, run, results
    │   ├── components/       # ui/, layout/, upload/, variants/, analysis/
    │   ├── hooks/            # use-project, use-sse, use-keyboard-shortcuts
    │   ├── lib/              # api-client.ts, types.ts, utils
    │   └── store/            # project-store (Zustand)
    └── package.json
```

---

## Tech stack

- **Backend**: Python 3.11+, FastAPI, SQLite (SQLAlchemy), statsmodels, LiteLLM.
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind, shadcn/ui, Zustand. API via `lib/api-client.ts`; progress via SSE.

---

## Grammar features (Ziems Multi-Value)

- **Source**: All features are aligned with the Ziems et al. Multi-Value paper (eWAVE-style; Section 3 tables: Pronouns, Noun Phrases, Tense/Aspect, Mood, Verb Morphology, Negation, Agreement, Relativization, Complementation, Adverbial, Adverbs/Prepositions, Discourse).
- **Count**: **189** features total (official code-implemented set). Metadata in `shared/grammar_features.json`; registry loads from there. Build script: `scripts/build_grammar_features_full.py`. Official list excludes plural_preposed, plural_postposed, bare_past_tense_2; includes fixin_future, got, ass_pronoun (see `docs/ZIEMS_MULTIVALUE_MAPPING.md`).
- **Transforms**: **189** features have real string transforms (text changes when applied). Each matches documented example_var; tests require 189/189.
- **Detection**: **189** applicability checks detect their canonical `example_std` as applicable; tests require 189/189.
- **Where**: Transforms and applicability in `backend/engine/grammar/transforms.py`; registry in `backend/engine/grammar/registry.py`. Paper–PARSE mapping and feasibility: `docs/ZIEMS_MULTIVALUE_MAPPING.md`.
- **Generalization**: `backend/tests/test_grammar_generalization.py` tests detection/rewrite on lexical variants of `example_std` and low false positives on decoys. Detection threshold 70%; features whose trigger word is in the substitution lexicons are exempt (`DETECTION_THRESHOLD_EXEMPT`).

### Grammar (complete)

- All **189** features have real transforms and match their documented `example_var` for `example_std`. All **189** applicability checks detect their `example_std` as applicable. See `context/DEVLOG.md`.

---

## Key entry points

| Want to…                    | Look at |
|----------------------------|--------|
| Understand API surface     | `backend/README.md` (full endpoint list) |
| Add a grammar feature      | `backend/README.md` § “How to Add New Grammar Features” + `backend/engine/grammar/transforms.py` |
| Add a new parser           | `backend/README.md` § “How to Add New Parsers” + `backend/llm/parsers.py` |
| Understand frontend flow   | `frontend/README.md` + `frontend/src/app/project/[id]/results/page.tsx` (analysis tabs) |
| Add a new analysis view     | `frontend/README.md` § “How to Add a New Analysis View” |
| Upload / column mapping    | `backend/routers/projects.py` (_detect_columns, _rows_from_upload, map-columns) |
| Variant generation logic   | `backend/engine/combinator.py` (generate_grammar_variants, generate_typo_variants, generate_all_variants) |

---

## Conventions

- **Backend**: Routers under `/api/<resource>`. Exceptions in `utils/errors.py`; handlers in `main.py`. DB session via `get_db()`.
- **Frontend**: Project-scoped state in Zustand (`project-store`). Grammar applicability is auto-scanned on upload (and when configure loads with existing prompts); results live in `grammarConfig.applicabilityResults`, `scanned`, `scanLoading` and persist across tab switches. Run selection and analysis data live in results page state; tables get flattened rows + optional `projectId`/`runIds` for export.
- **Parsers**: Return dict with at least `parsed_label`, `parsed_index`, `is_valid` for Likert-style tasks; runner stores these in `Result`.

---

## High-level vs code-level understanding

The four files (this CONTEXT + root README + backend README + frontend README) give a **solid high-level understanding**: what PARSE is, how frontend/backend are intended to work, the API surface, and main extension points. That is enough for an LLM to navigate the repo and make reasonable changes.

They do **not** give “full understanding of the code” for non-trivial edits: the READMEs describe *interfaces and intent*, not exact internal behavior and edge cases. For that you need the **internal specification** below and/or the **truth files** listed in “What to drag”.

---

## Internal specification (for non-trivial edits)

### Database schema and invariants

- **Tables**: `Project` (id TEXT PK, name, task_modality, created_at, config JSON). `Prompt` (id INTEGER PK, project_id FK, prompt_id TEXT logical id, prompt_text, variant TEXT, features_applied JSON, metadata_ JSON). `Run` (id TEXT PK, project_id FK, model_provider, model_id, system_prompt, temperature, status, started_at, completed_at, total_prompts, completed_prompts, error_count, progress_message). `Result` (id INTEGER PK, run_id FK, prompt_id FK → **Prompt.id** not logical prompt_id, raw_response, parsed_label, parsed_index, is_valid INT 0/1, error_message, latency_ms, created_at). `UploadStaging` (project_id PK, row_index PK, data JSON); FK to projects with ondelete=CASCADE.
- **Uniqueness**: No unique constraint on `(project_id, prompt_id, variant)`. One `Result` per (run_id, prompt_id) where prompt_id = `Prompt.id` (so one result per run per prompt *row*). Runs require at least one prompt row with variant=`"standard"` per logical prompt_id (see runs router).
- **Cascades**: Deleting a project is not defined in the snippet; upload_staging has CASCADE. When **grammar/typo generate** runs: all `Result` for runs of that project are deleted, then all `Run`, then all `Prompt` for the project, then new prompts (standard + grammar + typo variants) are inserted. So grammar/typo generate **replaces** all prompts for the project.
- **Baseline vs variant**: Baseline = prompt row with `variant="standard"`. Stored in same table: `variant` is `"standard"` | grammar feature id (e.g. `copula_deletion`) | typo feature id (e.g. `typo_char_swap`) | dialect id (e.g. `aave`, `chinese_simplified`). Analysis uses `baseline_variant="standard"` by default to compare other variants.

### Variant-generation semantics

- **Naming**: Grammar: `variant_id` = feature id (individual), or `"f1+f2"` sorted (bundle/combinations). Typo: `variant_id` = typo feature id (e.g. `typo_char_swap`). Cross grammar+typo (when `include_cross_combinations`): `variant_id` = `"{grammar_id}+{typo_id}"`. Dialect: `variant` stored as dialect id (e.g. `aave`, `chinese_simplified`).
- **Seeds**: Single global `seed` (default 42) per generate call. Typo transforms use `random.seed(seed)` before generating; same seed gives reproducible typo variants. Grammar is deterministic (no seed).
- **Collisions**: No dedupe by (prompt_id, variant). Running dialect generate twice appends duplicate (prompt_id, variant) rows. Grammar/typo generate replaces all prompts so no duplicate standard rows from that path.
- **Dialect vs grammar/typo**: Dialect generation **appends** new `Prompt` rows: for each *existing* prompt row and each selected dialect_id, adds a row with same logical prompt_id, rewritten text, `variant=dialect_id`. It does not delete existing prompts. So after grammar/typo generate you have standard + grammar + typo; after dialect you additionally have one row per (existing row × dialect). Run execution iterates all prompt rows (so each variant is queried once per run).

### Run execution, rate limits, retries

- **API key**: Before creating a run, backend validates that openai/anthropic/gemini have an API key (request body or env: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY). Empty string normalized to None. LiteLLM called with `base_url` (not `api_base`) and 120s timeout per request.
- **Concurrency**: `asyncio.gather` over batches of prompts; semaphore of 5 limits concurrent LLM calls. Batch size 10; after each batch, DB commit (results + completed_prompts).
- **Retries**: On 429/rate-limit, up to `RATE_LIMIT_MAX_RETRIES` (5) with exponential backoff: delay = `RATE_LIMIT_INITIAL_DELAY * (RATE_LIMIT_BACKOFF_FACTOR ** attempt)`, progress_message set to "rate limited, retrying...".
- **Fail-fast**: If the first batch has only errors and any looks like auth (e.g. "api key", "401"), run is marked failed immediately with that message.
- **Idempotency / partial results**: Before starting, runner skips prompts that already have a `Result` for this run_id. So resuming is “run again, only pending get queried”. No per-prompt idempotency key; one row per (run_id, Prompt.id).
- **Failure modes**: Background run task catches exceptions and sets run status to `failed` with progress_message. Non–rate-limit errors: one `Result` row with error_message set, raw_response/parsed_* null, is_valid not set; `error_count` incremented; run still continues and eventually marks completed. Cancel: `_cancelled` flag; after current batch, run status set to `cancelled` and completed_at set.
- **Progress stream**: `GET /{run_id}/progress/stream` uses a fresh DB session per poll (SessionLocal() in loop) so it reads latest committed completed_prompts. Frontend also polls `GET /{run_id}/progress` every 2s when runs are active as fallback.

### Parsing contract per modality

- **What gets stored in Result**: Runner always stores `parsed_label`, `parsed_index`, `is_valid` (0/1). From parser output it uses only those three keys (and coerces parsed_index to int, is_valid to bool). Other parser return keys (e.g. `titles`, `word_count`) are not persisted.
- **Likert**: `parsed_label` = canonical label string (1 = "strongly unacceptable", 5 = "strongly acceptable"; "completely" variants still parse but canonical is "strongly"), `parsed_index` = 1–5, `is_valid` = True if number or label matched. Valid = response contains a 1–5 digit or a phrase in LABEL_MAP.
- **recommendation_list**: Parser returns `titles`, `count`, `is_valid`; runner still only writes parsed_label/parsed_index/is_valid (so parsed_index typically unused; is_valid = len(titles)>0).
- **free_text**: Parser returns `text`, `word_count`, `is_valid`, `is_refusal`; only `is_valid` is stored in Result. Completeness analysis uses `raw_response` for refusal detection and uses `parsed_index.notna()` or `is_valid==1` for valid count.

### Analysis math

- **Difference (LPM)**: For each (model_id, variant_id) with variant ≠ baseline: (1) Join variant rows with baseline on (prompt_id, model_id); (2) drop rows where parsed_index or baseline_parsed_index is NaN; (3) binary `changed = (parsed_index != baseline_parsed_index)`; (4) OLS `y ~ 1` (intercept only). Intercept = difference rate; SE, t, p-value, 95% CI from OLS. Significance stars: *** p<0.001, ** p<0.01, * p<0.05. No multiple-testing correction. n_obs < 2: rate = mean(y), SE=0, p_value=1.
- **Directional bias**: Same join/drop; then `diff = parsed_index - baseline_score`; OLS `diff ~ 1`. β₀ = mean_difference; direction = higher | lower | neutral from sign of β₀. Same SE/t/p/CI/significance.
- **Completeness**: Per (model_id, variant_id): total = count of rows; valid = parsed_index.notna().sum() or (is_valid==1).sum(); refusals = count of raw_response matching REFUSAL_PATTERNS; empty = blank raw_response; invalid = total - valid; valid_rate = valid/total, refusal_rate = refusals/total.

### Frontend state and data coupling

- **Run selection**: `selectedRunIds` lives in Zustand (`project-store`). Not persisted to URL or localStorage; resets when store is reset (e.g. project change). **Results page**: when there are completed runs and none selected, an effect auto-selects all completed runs so data loads immediately. Results page fetches completeness/difference/directional when `projectId` or `selectedRunIds` changes (effect deps on `selectedIdsArray.join(',')`).
- **Caching**: No HTTP cache headers documented; frontend does not implement its own cache layer for analysis endpoints. Each tab’s data is fetched when selection changes.
- **Errors/toasts**: API client throws on non-ok response; callers use .catch() or toast (e.g. sonner). Global error toast and error boundary exist; analysis tables show loading/empty states.
- **Backend → frontend shapes**: Difference/directional: `Record<model_id, Record<variant_id, { difference_rate | mean_difference, se, t_stat, p_value, n_obs, ci_lower, ci_upper, significance[, direction] }>>`. Completeness: `Record<model_id, Record<variant_id, { total, valid, invalid, refusals, empty, valid_rate, refusal_rate }>>`. Flatten helpers: `flattenDifference` / `flattenDirectionalBias` produce rows with snake_case keys from API mapped to camelCase (e.g. difference_rate → differenceRate); `flattenCompleteness` same. Charts and tables consume these flattened rows.

---

## What to drag for “full” context

- **Devlog**: `context/DEVLOG.md` — session changelog (run UX, progress, results, Likert, API key). Use when continuing from a recent session.
- **Minimal (high-level)**: `context/CONTEXT.md` + `README.md` → goal, scope, structure, architecture.
- **Full docs (no code)**: Add `backend/README.md` and `frontend/README.md` → APIs, extension points, how-to.
- **Non-trivial edits (truth files)**: To close the gap between intent and exact behavior, add the “source of truth” files:
  - **Backend**: `backend/db.py`, `backend/engine/combinator.py`, `backend/routers/variants.py` (generate + _get_base_prompts), `backend/llm/runner.py`, `backend/analysis/difference.py`, `backend/analysis/directional_bias.py`, `backend/analysis/completeness.py`, and (if export/LaTeX matters) `backend/analysis/export.py`.
  - **Frontend**: `frontend/src/lib/api-client.ts`, `frontend/src/lib/types.ts`, `frontend/src/app/project/[id]/results/page.tsx`, and the analysis table components that define the flatten helpers: `difference-table.tsx`, `directional-bias-table.tsx`, `completeness-table.tsx`.

With **CONTEXT + three READMEs**, an LLM can navigate and make reasonable changes. With **CONTEXT + READMEs + truth files** (or the internal spec above), it can implement fixes and features with minimal back-and-forth.
