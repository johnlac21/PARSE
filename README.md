# PARSE Framework
**Prompt Alteration Response-Shift Evaluation**

A full-stack web application for generating linguistic prompt variants, querying LLMs, and analyzing output shifts.

## Features
- Upload baseline prompts (CSV/JSONL)
- Generate grammar variants (189 features from Ziems Multi-Value paper; all have real transforms that match documented examples)
- Generate typo variants (6 types with configurable intensity)
- Generate dialect/language variants via LLM rewriting
- Query multiple LLMs with all variants
- Statistical analysis: difference (LPM), directional bias, completeness
- Export results as LaTeX, CSV, JSON

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- (Optional) Docker & Docker Compose

### Option 1: Docker
```bash
docker-compose up
```
Frontend: http://localhost:3000  
Backend: http://localhost:8000

### Option 2: Manual Setup
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

## Architecture

- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui. Calls backend REST API; optional SSE for run progress.
- **Backend**: FastAPI + SQLite (SQLAlchemy) + statsmodels for LPM/directional bias. Routers: projects, variants, runs, analysis, dialect.
- **LLM integration**: LiteLLM (unified interface for OpenAI, Anthropic, etc.). Responses are parsed by task-specific parsers. v1 exposes Likert only; recommendation_list and free_text parsers are scaffolded for future releases.
- **Data flow**: Projects → Prompts (baseline + variants) → Runs (model + config) → Results (raw_response, parsed_index, is_valid). Analysis endpoints consume results and return difference/completeness/directional bias; export produces LaTeX/CSV/JSON.

## Supported task modalities

PARSE v1 supports **Likert-scale evaluation** only. The framework architecture is modality-agnostic — output parsers for recommendation lists and free-text are scaffolded in `backend/llm/parsers.py` and can be re-enabled by:

1. Adding the desired modality back to the `TaskModality` literal in `backend/models/schemas.py`.
2. Re-exposing it in the create-project dialog (`frontend/src/components/create-project-dialog.tsx`).
3. Extending the runner's storage logic in `backend/llm/runner.py` to persist modality-specific parser fields.
4. Defining appropriate analysis metrics for the modality (the current Difference / Directional Bias analyses assume Likert numerical responses).

See the [Roadmap](#roadmap) for planned multi-modality support.

## Grammar Features

**189 features** total, aligned with the Ziems Multi-Value paper (eWAVE-style; Tables 7–18). Metadata in `shared/grammar_features.json` (project root); registry loads from there. All **189** have real transforms; for each feature, `apply_grammar(example_std, feature_id)` equals the documented `example_var`. All **189** applicability checks detect their `example_std` as applicable (detection correctness). See `context/CONTEXT.md` § Grammar features and `docs/ZIEMS_MULTIVALUE_MAPPING.md`. Rebuild: `python scripts/build_grammar_features_full.py`. The official 189 are the code-implemented set (excludes plural_preposed, plural_postposed, bare_past_tense_2; includes fixin_future, got, ass_pronoun).

Transforms are defined in `backend/engine/grammar/transforms.py`. Sample of implemented features (standard → variant):

| Feature ID | Description | Example (standard → variant) |
|------------|-------------|-----------------------------|
| `drop_articles` | Remove definite/indefinite articles | "the movie" → "movie" |
| `drop_prepositions` | Drop *to* after go/come, *at* after look | "go to the store" → "go the store" |
| `copula_deletion` | Omit *is/are/am* (not before -ing) | "She is happy" → "She happy" |
| `aint_negation` | Generalize negations to *ain't* | "is not" → "ain't" |
| `habitual_be` | Habitual *be* (e.g. AAVE) | "She likes it" → "She be liking it" |
| `drop_auxiliary` | Omit perfect have/has/had | "have seen" → "seen" |
| `drop_subject_pronoun` | Drop I/He/She/We/They at sentence start | "I want that" → "Want that" |
| `was_leveling` | *were* → *was* | "They were here" → "They was here" |
| `them_as_demonstrative` | *those/these* → *them* | "those books" → "them books" |
| `g_dropping` | -ing → -in' (excluding thing, ring, etc.) | "running" → "runnin'" |
| `negative_concord` | *any* → *no* in negated clauses | "don't have any" → "don't have no" |
| `fixin_to` | *about to / going to* → *fixin' to* | "going to leave" → "fixin' to leave" |
| `completive_done` | *have/has/had* + V → *done* + V | "have eaten" → "done eaten" |
| `existential_it` | *there is/are/was/were* → *it's / it was* | "There is a cat" → "It's a cat" |
| `possessive_s_absence` | Remove possessive 's (not it's, he's, etc.) | "John's book" → "John book" |
| `yall_pronoun` | *you all / you guys / both of you* → *y'all* | "you all" → "y'all" |
| `contraction_gonna` | *going to* (before verb) → *gonna* | "going to see" → "gonna see" |
| `contraction_wanna` | *want to* → *wanna* | "want to go" → "wanna go" |
| … plus paper features (e.g. `double_modals`, `who_what`, `got_gotten`, `uninflect`, `what_comparative`, `drop_inf_to`, `your_yalls`, `here_come`, `past_tense_leveling`). |

Grammar feature set is complete: all 189 have real transforms that match their documented example_var, and all 189 applicability checks detect their example_std as applicable. Generalization tests: `backend/tests/test_grammar_generalization.py` (70% detection on variants; features in `DETECTION_THRESHOLD_EXEMPT` excluded where trigger is substituted).

## Typo Features (6 types)

| Feature ID | Description | Example |
|------------|-------------|---------|
| `typo_keyboard_prox` | Adjacent QWERTY key substitution | "film" → "fklm" |
| `typo_char_swap` | Swap two adjacent characters | "recommend" → "reocmmend" |
| `typo_char_double` | Double a character | "movie" → "moovie" |
| `typo_char_delete` | Delete one character (mid-word) | "recommend" → "recomend" |
| `typo_whitespace` | Remove or add spaces | "I want a movie" → "I wanta movie" |
| `typo_typoglycemia` | Shuffle middle letters (first/last fixed) | "recommend" → "rceomemnd" |

Word and character application probabilities are configurable (`typo_word_p`, `typo_char_p`).

## API Documentation

FastAPI auto-generates interactive docs at **http://localhost:8000/docs** (Swagger UI) and **http://localhost:8000/redoc**.

## Testing

```bash
cd backend
pytest tests/ -v
```

Grammar generalization tests (`backend/tests/test_grammar_generalization.py`) check that applicability and transforms generalize to lexical variants of `example_std` (template-based substitution) and that decoy sentences are not over-detected; run with `PYTHONPATH=. pytest tests/test_grammar_generalization.py -q`.

## Citation

If you use this tool in your research, please cite:

> **Note**: A paper describing PARSE is forthcoming. The BibTeX entry below is a placeholder; final author/institution/year fields will be filled in upon publication.

```bibtex
@mastersthesis{parse2025,
  title  = {PARSE Framework: Prompt Alteration Response-Shift Evaluation},
  author = {[Your Name]},
  school = {[Your Institution]},
  year   = {2025},
  type   = {Master's thesis}
}
```

Adjust the entry as needed for your thesis or paper format.

## Roadmap

- **Multi-modality analysis (recommendation lists, free text)**: Re-expose non-Likert modalities in the API and UI; wire scaffolded parsers end-to-end with modality-specific metrics.
