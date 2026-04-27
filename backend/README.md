# PARSE Backend

FastAPI application providing the PARSE API: projects, prompt uploads, variant generation, LLM runs, and statistical analysis.

## API Endpoints

All routes are under `/api/`. Base URL when running locally: `http://localhost:8000`.

### Projects (`/api/projects`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/` | Create project (name, task_modality). Returns project with id. |
| GET | `/` | List all projects. |
| GET | `/{project_id}` | Get project by id. |
| DELETE | `/{project_id}` | Delete project (cascades to prompts, runs, results). |
| POST | `/{project_id}/upload` | Upload CSV/JSONL file. Auto-detects columns or returns sample for column mapping. |
| POST | `/{project_id}/upload/map-columns` | Apply column mapping to staged upload (prompt_id_column, prompt_text_column, variant_column, metadata_columns). |
| GET | `/{project_id}/prompts` | Paginated prompts (query: page, per_page). |

### Variants (`/api/variants`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/grammar-features` | List registered grammar features (id, name, description, example_std, example_var, category, etc.). |
| GET | `/typo-features` | List registered typo features (id, name, description, example, default_word_p, default_char_p). |
| POST | `/preview` | Preview variants for 1–10 sample texts (grammar/typo features, modes, seed). Returns variant list and counts. |
| POST | `/check-applicability` | Batch applicability for grammar features on all prompts in a project. |
| POST | `/generate` | Generate and persist variants for project (grammar/typo/dialect options). Returns variants_generated count. |

### Runs (`/api/runs`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/models` | List available LLM models (provider/model id). |
| POST | `/create` | Create and start a run (project_id, model_provider, model_id, system_prompt, temperature, etc.). Returns run with id. |
| GET | `/{run_id}/progress` | Current run progress (status, completed_prompts, total_prompts, progress_message). |
| GET | `/{run_id}/progress/stream` | SSE stream of progress events. |
| POST | `/{run_id}/cancel` | Cancel a running job. |
| GET | `/project/{project_id}` | List runs for project. |

### Analysis (`/api/analysis`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/difference` | LPM difference analysis (project_id, run_ids, baseline_variant). Returns per-model, per-variant difference rate, SE, p-value, significance. |
| POST | `/directional-bias` | Signed difference vs baseline (project_id, run_ids, baseline_variant). Returns mean_difference, SE, p-value per variant per model. |
| POST | `/completeness` | Valid/total and valid_rate per variant per model (project_id, run_ids). |
| POST | `/export` | Export analysis as LaTeX, CSV, or JSON (project_id, run_ids, table_type, format). |
| GET | `/results/{project_id}` | Raw results with filters (run_id, variant, model_id, page, per_page). |

### Dialect (`/api/dialect`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/available` | List available dialect configs (id, name, type, requires_llm, examples). |
| POST | `/test-connection` | Test LLM connection (provider, api_key, model, base_url). |
| POST | `/rewrite-preview` | Preview dialect rewrites for 1–3 texts (dialect_ids, provider, api_key, model, constrained, etc.). |
| POST | `/generate` | Start background dialect variant generation; returns job_id. |
| GET | `/generate/{job_id}/progress` | Progress for dialect generation job. |

---

## How to Add New Grammar Features

1. **Metadata (optional)**  
   Add an entry to `backend/shared/grammar_features.json` under `"features"` with: `id`, `name`, `description`, `example_std`, `example_var`, `category`, `dialects`, `requires_pos_tags`, `tier`, `source`. If the file is missing, the app still runs but only features that are both in JSON and have a transform (below) will be fully available.

2. **Transform and applicability**  
   In `backend/engine/grammar/transforms.py`:
   - Implement `_transform_<feature_id>(text: str) -> str` and `_applicability_<feature_id>(text: str) -> dict` (dict with keys: `applicable`, `match_count`, `match_positions`, `reason`).
   - In `_register_all_transforms()`, add a tuple: `("<feature_id>", _transform_<feature_id>, _applicability_<feature_id>)`.
   - On startup, `load_features_from_json()` loads metadata into `GRAMMAR_REGISTRY`, then each registered pair attaches `transform` and `applicability_check` to the corresponding `GrammarFeature`. The feature id must exist in the JSON (or be created programmatically) for `get_feature(feature_id)` to succeed.

3. **Registry**  
   Grammar features are stored in `engine.grammar.registry.GRAMMAR_REGISTRY`. New features are picked up by `GET /api/variants/grammar-features`, variant preview, and variant generation once registered.

---

## How to Add New Parsers

Parsers turn raw LLM output into structured fields for storage and analysis (e.g. `parsed_label`, `parsed_index`, `is_valid`).

1. **Implement a parser**  
   In `backend/llm/parsers.py`:
   - Subclass `OutputParser` and implement `parse(self, raw_response: str) -> dict`.
   - Return a dict that includes at least what the run pipeline expects: for Likert-style tasks, `parsed_label`, `parsed_index`, `is_valid`; other modalities may use `titles`, `text`, `word_count`, etc.

2. **Register the parser**  
   In `get_parser(task_modality: str)` in the same file, add a new branch, e.g.:
   - `"your_modality": YourParser()`.

3. **Use the new modality**  
   - Add the new modality to the `TaskModality` literal in `backend/models/schemas.py` (e.g. `Literal["likert", "recommendation_list", "free_text", "your_modality"]`).
   - Ensure projects can be created with `task_modality="your_modality"` (e.g. in the frontend create-project flow and any validation).

4. **Runner**  
   `llm/runner.py` uses `get_parser(self.task_modality)` and calls `parser.parse(raw_response)`. It stores `parsed_label`, `parsed_index`, and `is_valid` from the returned dict; extend the runner or DB schema if your parser returns additional fields that should be persisted.

---

## Project Layout (backend)

- `main.py` — FastAPI app, CORS, routers, startup (DB + grammar/typo load), exception handlers.
- `db.py` — SQLAlchemy models (Project, Prompt, Run, Result, UploadStaging) and session handling.
- `models/schemas.py` — Pydantic request/response models.
- `routers/` — projects, variants, runs, analysis, dialect.
- `engine/` — grammar (registry, transforms, applicability), typos (registry, transforms), combinator (variant generation), dialect (config, LLM rewriter).
- `llm/` — providers (LiteLLM wrapper), runner (async run execution), parsers (Likert, recommendation list, free text).
- `analysis/` — difference (LPM), directional_bias, completeness, export (LaTeX, CSV, JSON).
- `utils/` — errors (custom exceptions), startup (load transforms, feature counts).
- `shared/` — optional `grammar_features.json` for grammar metadata.
