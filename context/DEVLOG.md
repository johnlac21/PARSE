# PARSE Devlog

Changelog of notable changes (agentic session). Use for context when continuing work.

---

## TODO (current)

- Grammar: **189/189** features (official code-implemented set) have real transforms and match documented `example_var`. **189/189** applicability checks detect canonical `example_std`. Official list: build script (no plural_preposed, plural_postposed, bare_past_tense_2; yes fixin_future, got, ass_pronoun). Tests: `test_grammar_transforms.py`; `test_grammar_generalization.py` (70% detection). No open grammar TODO.

---

## Session (Grammar: generalization tests + applicability widenings)

- **Generalization test suite**: Added `backend/tests/test_grammar_generalization.py` — template-based lexical variants of `example_std`, detection hit rate ≥70% (features in `DETECTION_THRESHOLD_EXEMPT` excluded when trigger word is in substitution lexicons), rewrite sanity, false positive rate ≤30% on decoys. Fixed seed for CI.
- **Fixes**: `plural_preposed` — applicability/transform restricted to determiner/gerund context (fewer FPs). `invariant_tag_can_or_not` — test allows 3× length ratio for tag-style output.
- **Applicability widenings**: Many features had patterns widened (e.g. acomp_focusing_like, degree_adj_for_adv, object_pronoun_drop, benefactive_dative, indefinite_for_zero, referential_thing, participle_past_tense, past_tense_leveling, progressives, that_infinitival_subclause, to_infinitive, transitive_suffix, superlative_before_matrix_head, clause_final_really_but, third_person_s_absence, drop_prepositions). Canonical tests unchanged (204/204).

---

## Session (Grammar: applicability 204/204)

- **Goal**: Ensure all 204 features report `applicable=True` for their own `example_std` (detection correctness).
- **Done**: Fixed 4 features whose applicability did not detect their canonical example: `habitual_be` (added `_HABITUAL_ALWAYS` for They/We/You are always), `aspect_been` (added `_HAS_HAVE_BEEN` for has/have been), `bare_past_tense_2` (new `_applicability_bare_past_tense_2` for regular -ed verbs), `preposition_chopping` (regex now allows final `on?`). Tightened test `test_applicability_detects_canonical_example_for_every_feature` to require 204/204.

---

## Session (Grammar: Option B — transforms match example_var)

- **Goal**: For each feature, make `apply_grammar(example_std, feature_id)` equal the documented `example_var` (transforms only).
- **Done**: Fixed who_what, added volition_changes/yall/future_sub_gon/finna_future, plural_s_absence, nasal_possessive_pron, bare_past_tense_2; fixed 27 other transforms. Test requires 204/204 match.

---

## Session (Grammar: batch 11 — final 26 → 204 real, 0 no-op)

- **Goal**: Implement the remaining 26 no-op grammar features so the full set of 204 has real transforms.
- **Done**: Added 26 new real transforms: it_is_referential, it_is_non_referential, em_subj_pronoun, em_obj_pronoun, non_coordinated_subj_obj, non_coordinated_obj_subj, existential_possessives, possessives_for_post, possessives_for_pre, possessives_belong, mass_noun_plurals, that_resultative_past_participle, medial_object_perfect, serial_verb_give, serial_verb_go, transitive_suffix, shadow_pronouns, one_relativizer, analytic_whose_relativizer, correlative_constructions, doubly_filled_comp, inverted_indirect_question, clefting, fronting_pobj, superlative_before_matrix_head, chaining_main_verbs. **204** real transforms; **0** no-op.

---

## Session (Grammar: batch 10 — 16 new transforms + 1 alias → 178 real, 26 no-op)

- **Goal**: Continue implementing the remaining no-op grammar features.
- **Done**: Added 16 new real transforms in `backend/engine/grammar/transforms.py`: benefactive_dative, regularized_reflexives (himself→hisself), regularized_reflexives_object_pronouns (myself→meself), regularized_reflexives_aave (themselves→theyselves), reflex_number (ourselves/themselves→ourself/themself), emphatic_reflex (themselves→their own self), absolute_reflex (and he and→and himself and), reduplicate_interrogative (Who's→Who-who's), anaphoric_it (than they→than it), null_relcl (the N who V→the N V), plural_preposed (Ns→alla N), plural_postposed (The Ns→Da N dem), plural_to_singular_human (people→person), relativizer_doubling (who→that which), it_dobj (explained/said to→explained/said it to), no_gender_distinction (he/she→they, him→them). Registered alias: nasal_possessive_pron→my_me. **178** real transforms; **26** no-op.

---

## Session (Grammar: batch 9 — 9 new transforms + 4 aliases → 161 real, 43 no-op)

- **Goal**: Continue implementing the remaining no-op grammar features.
- **Done**: Added 9 new real transforms: your_yalls, me_us, here_come, plural_interrogative, myself_coordinate_subjects, zero_plural_after_quantifier, give_passive, double_obj_order, past_tense_leveling. Registered 4 aliases: bare_past_tense_2, plural_s_absence, null_referential_pronouns, aspect_been. **161** real transforms; **43** no-op.

---

## Session (Grammar: 99 new real transforms → 148 total)

- **Goal**: Implement more of the 204 grammar features so more variants actually modify text.
- **Done**: Added 99 new real transforms in `backend/engine/grammar/transforms.py` in 8 batches (batches 2–8), covering article swaps, negation, tense/aspect, comparatives/superlatives, existentials, invariant tags, wh/yn aux drop, quotative/focusing like, possessives (my→me, our→us, etc.), object pronoun drop, say/for complementizers, for_to, bare_ccomp, negative inversion, clause_final though/really_but, me_coordinate_subjects, subord/corr conjunction doubling, linking_relcl, reduced_relative, that_infinitival_subclause, proximal_distal_demonstratives, adj_postfix, present_for_exp_perfect, she/he inanimate, referential_thing, you_ye, be_perfect, irrealis_be_done, present_perfect_ever, perfect_already, perfect_slam, relativizer_where, to_infinitive, after_perfect, and others.
- **Counts**: **148** features now have real transforms; **56** remain no-op. Context files updated with new counts.

---

## Session (Ziems Multi-Value grammar — 204 features)

### Goal

Integrate all 100+ grammar features from the Ziems Multi-Value paper so every paper feature appears in the app.

### What was done

- **Full feature list**: Added 176 paper features to the existing 28 PARSE features → **204 total**. Metadata in `shared/grammar_features.json` (id, name, description, example_std, example_var, category, dialects, source). Build script: `scripts/build_grammar_features_full.py` (re-runnable; keeps existing 28, adds missing paper features).
- **Transforms**: 49 features have real transforms (24 original PARSE + 14 paper ids mapped to same impl + 11 new: double_modals, who_what, got_gotten, drop_aux_be_gonna, wasnt_werent, regularized_past_tense, participle_past_tense, uninflect/third_person_s_absence, preposition_chopping, what_comparative, drop_inf_to). Paper ids that reuse existing transforms: e.g. drop_copula_be_NP/AP/locative → copula_deletion; those_them, were_was, null_genitive, yall, finna_future, future_sub_gon, volition_changes, drop_aux_have, null_prepositions, remove_det_*, aint_*.
- **No-op for the rest**: 56 features have no real transform yet. They use `_transform_noop` (identity) and `_applicability_noop` (always not applicable) so they appear in the grammar panel and can be selected without errors; applying them leaves text unchanged.
- **Docs**: `docs/ZIEMS_MULTIVALUE_MAPPING.md` — paper tables, PARSE↔paper mapping, feasibility (regex vs POS). Context files updated (CONTEXT.md, README, backend/frontend README copies) with counts and TODO.

### Files touched

| Area | Files |
|------|--------|
| Grammar data | `shared/grammar_features.json` (204 entries), `scripts/build_grammar_features_full.py` (generator) |
| Grammar engine | `backend/engine/grammar/transforms.py` (no-op, paper-id→transform mapping, 11 new transforms, fallback no-op registration) |
| Docs | `docs/ZIEMS_MULTIVALUE_MAPPING.md` (mapping + status), `context/CONTEXT.md`, `context/README.md`, `context/DEVLOG.md`, `context/backen d_README.md` |

---

## Session (Run UX, Results, Likert, Progress)

### Run execution & API

- **API key validation**: Before creating a run, backend now requires an API key for openai/anthropic/gemini (either in request body or via env: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`). Returns 400 immediately with a clear message if missing. Empty string in request is normalized to `None` so env is used.
- **LiteLLM call fix**: Provider now passes `base_url` (not `api_base`) to `litellm.acompletion()` and sets `timeout: 120` per request to avoid hanging.
- **create_run**: Endpoint changed to `async def create_run` so the background task runs correctly on the event loop.
- **Background task error handling**: `_execute_run_background` catches exceptions, sets run status to `failed` and `progress_message` to the error text, and logs. Run no longer stays "running" at 0 with no feedback.
- **Fail-fast on auth errors**: After the first batch, if every result is an error and any looks like auth (e.g. "api key", "401", "unauthorized"), the run is marked failed immediately with that message instead of processing all prompts.
- **Progress message at start**: Run row gets `progress_message = "Starting..."` as soon as the background task starts so the UI shows something before the first batch.

### Progress bar

- **Stale progress**: SSE progress stream was reusing the same request DB session; SQLAlchemy returned the same cached `Run` so `completed_prompts` never updated. Fixed by using a **fresh session per poll**: inside the event generator, each loop opens `SessionLocal()`, queries `Run`, builds payload, closes session. Stream now sends latest committed progress.
- **Stream completion**: Progress stream now treats `failed` like `completed`/`cancelled` (sends final event and closes).
- **Frontend fallback**: Run page polls `GET /api/runs/{runId}/progress` every 2 seconds for active runs so the bar updates even if SSE is unreliable (e.g. proxies).

### Results page

- **No data when run selected**: Layout was clearing `selectedRunIds` on project load, so opening Results showed no selection and no fetch. When the user checked a run, data could load, but the common case (open Results after a run) showed "No completeness data". Fixed by **auto-selecting all completed runs** when there are completed runs and none selected, so completeness/difference/directional fetch immediately and tables populate.

### Likert scale wording

- **Canonical labels**: Switched from "completely acceptable" / "completely unacceptable" to **"strongly acceptable"** / **"strongly unacceptable"** for the Likert scale.
- **Default system prompt** (Run page): Prompt text now says 1 = 'strongly unacceptable', 5 = 'strongly acceptable'.
- **Backend parser** (`llm/parsers.py`): `LABEL_MAP` lists "strongly" first; `_index_to_label()` returns "strongly unacceptable" (1) and "strongly acceptable" (5). "Completely" variants still parse (kept as aliases).
- **Parser test**: `test_written_out_completely_unacceptable` renamed to `test_written_out_strongly_unacceptable` and asserts "strongly unacceptable".

### UI copy

- Run page API Key field placeholder: now "Or set on server (e.g. OPENAI_API_KEY)".
- Run progress: status line always shown when running (e.g. "Starting…", "Running…") or the error message when failed.

---

## Files touched (summary)

| Area | Files |
|------|--------|
| Backend runs | `backend/routers/runs.py` (validation, normalize API key, fresh session in stream, async create_run, error handling, fail stream on failed) |
| Backend LLM | `backend/llm/providers.py` (base_url, timeout); `backend/llm/runner.py` (auth fail-fast, batch logging) |
| Backend parsers | `backend/llm/parsers.py` (Likert "strongly"); `backend/tests/test_parsers.py` (test name/assert) |
| Frontend run | `frontend/src/app/project/[id]/run/page.tsx` (default prompt, placeholder, status line, polling effect) |
| Frontend results | `frontend/src/app/project/[id]/results/page.tsx` (auto-select completed runs) |
| Context | `context/CONTEXT.md`, `context/backen d_README.md`, `context/Frontend_README.md` (minimal spec updates); `context/DEVLOG.md` (this file) |
