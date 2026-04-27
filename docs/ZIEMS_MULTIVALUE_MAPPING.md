# Ziems Multi-Value Paper ↔ PARSE Grammar Mapping

Reference: Ziems et al. Multi-Value paper (2212.pdf), Section 3 tables (Pronouns through Discourse).

The **official list of 189 grammar features** is the set actually implemented in the code (eWAVE-style IDs plus two extras: got, ass_pronoun). It does not include plural_preposed, plural_postposed, or bare_past_tense_2; it does include both finna_future and fixin_future.

## Current PARSE coverage (22 features in JSON, 18 with transforms)

| PARSE id | Paper equivalent(s) | Table |
|----------|----------------------|-------|
| drop_articles | remove_det_definite, remove_det_indefinite (partial) | NP |
| drop_prepositions | null_prepositions (partial) | Adv/Prep |
| copula_deletion | drop_copula_be_NP, drop_copula_be_AP, drop_copula_be_locative | Agreement |
| aint_negation | aint_be, aint_have, aint_before_main | Negation |
| habitual_be | (habitual interpretation of be) | Tense/Aspect |
| drop_auxiliary | drop_aux_have (partial) | Agreement |
| drop_subject_pronoun | null_referential_pronouns (partial) | Pronouns |
| was_leveling | were_was | Agreement |
| them_as_demonstrative | those_them | NP |
| g_dropping | a_ing (spelling variant), -in' | Verb Morph |
| negative_concord | negative_concord | Negation |
| fixin_to | finna_future, fixin_future | Mood |
| completive_done | completive_done | Tense/Aspect |
| existential_it | existential_it | Agreement |
| possessive_s_absence | null_genitive | NP |
| yall_pronoun | yall, your_yalls | Pronouns |
| contraction_gonna | future_sub_gon (gon') | Tense/Aspect |
| contraction_wanna | volition_changes (waan/wanna) | Tense/Aspect |
| third_person_s_absence | uninflect | Agreement (no transform yet) |
| plural_s_absence | zero_plural, etc. (no transform yet) | NP |
| past_tense_leveling | participle_past_tense, past_for_past_participle (no transform yet) | Verb Morph |
| aspect_been | past_been (no transform yet) | Tense/Aspect |

## Paper features by table (all from 2212.pdf)

### Table 7 – Pronouns (47 entries)
she_inanimate_objects, he_inanimate_objects, referential_thing, pleonastic_that, em_subj_pronoun, em_obj_pronoun, me_coordinate_subjects, myself_coordinate_subjects, benefactive_dative, no_gender_distinction, regularized_reflexives, regularized_reflexives_object_pronouns, regularized_reflexives_aave, reflex_number, absolute_reflex, emphatic_reflex, my_i, our_we, his_he, their_they, your_you, your_yalls, his_him, their_them, my_me, our_us, me_us, non_coordinated_subj_obj, non_coordinated_obj_subj, nasal_possessive_pron, yall, you_ye, plural_interrogative, reduplicate_interrogative, anaphoric_it, object_pronoun_drop, null_referential_pronouns, it_dobj, it_is_referential, it_is_non_referential

### Table 8 – Noun Phrases (no plural_preposed, plural_postposed in official list)
regularized_plurals, mass_noun_plurals, zero_plural_after_quantifier, plural_to_singular_human, zero_plural, double_determiners, definite_for_indefinite_articles, indefinite_for_definite_articles, remove_det_definite, remove_det_indefinite, definite_abstract, indefinite_for_zero, indef_one, demonstrative_for_definite_articles, those_them, proximal_distal_demonstratives, demonstrative_no_number, existential_possessives, possessives_for_post, possessives_for_pre, possessives_belong, null_genitive, double_comparative, double_superlative, synthetic_superlative, analytic_superlative, more_much, comparative_as_to, comparative_than, comparative_more_and, zero_degree, adj_postfix

### Table 9 – Tense and Aspect
progressives, standing_stood, that_resultative_past_participle, medial_object_perfect, after_perfect, simple_past_for_present_perfect, present_perfect_for_past, present_for_exp_perfect, be_perfect, do_tense_marker, completive_done, completive_have_done, irrealis_be_done, perfect_slam, present_perfect_ever, perfect_already, completive_finish, past_been, bare_perfect, future_sub_gon, volition_changes, come_future, present_for_neutral_future, is_am_1s, will_would, if_would

### Table 10 – Mood
double_modals, present_modals, finna_future, fixin_future

### Table 11 – Verb Morphology (no bare_past_tense_2 in official list)
regularized_past_tense, bare_past_tense, past_for_past_participle, participle_past_tense, double_past, a_ing, a_participle, transitive_suffix, got_gotten, verbal_ing_suffix, conditional_were_was, serial_verb_give, serial_verb_go, here_come, give_passive

### Table 12 – Negation
negative_concord, aint_be, aint_have, aint_before_main, dont, never_negator, no_preverbal_negator, not_preverbal_negator, nomo_existential, wasnt_werent, invariant_tag_* (4 types)

### Table 13 – Agreement
uninflect, generalized_third_person_s, existential_there, existential_it, drop_aux_be_progressive, drop_aux_be_gonna, drop_copula_be_NP/AP/locative, drop_aux_have, were_was

### Table 14 – Relativization
who_which, who_as, who_at, relativizer_where, who_what, relativizer_doubling, analytic_whose_relativizer, null_relcl, shadow_pronouns, one_relativizer, correlative_constructions, linking_relcl, preposition_chopping, reduced_relative

### Table 15 – Complementation
say_complementizer, for_complementizer, for_to_purpose, for_to, what_comparative, existential_got, existential_you_have, that_infinitival_subclause, drop_inf_to, to_infinitive, bare_ccomp

### Table 16 – Adverbial Subordination
clause_final_though_but, clause_final_really_but, chaining_main_verbs, corr_conjunction_doubling, subord_conjunction_doubling

### Table 17 – Adverbs and Prepositions
null_prepositions, degree_adj_for_adv, flat_adj_for_adv, too_sub

### Table 18 – Discourse and Word Order
clefting, fronting_pobj, negative_inversion, inverted_indirect_question, drop_aux_wh, drop_aux_yn, doubly_filled_comp, superlative_before_matrix_head, double_obj_order, acomp_focusing_like, quotative_like

### Extra (no eWAVE ID in code)
got (present-tense have/has → got), ass_pronoun (pronoun camouflage / intensifiers)

---

## Official list (189 features)

The official grammar feature set is the **189 features implemented in the code** (eWAVE-style IDs 1–235 plus the two extra features). This list removes plural_preposed, plural_postposed, bare_past_tense_2 and adds fixin_future, got, ass_pronoun. Rebuild: `python scripts/build_grammar_features_full.py`.

---

## Feasibility for PARSE

- **Already implemented (18):** See “Current PARSE coverage” above.
- **Regex/heuristic feasible (no POS):** dont, never_negator, conditional_were_was, double_modals, uninflect (third_person_s_absence), regularized_past_tense, participle_past_tense, got_gotten, degree_adj_for_adv, flat_adj_for_adv, drop_aux_be_gonna, existential_there (there’s + plural), who_what, invariant_tag variants (simple cases), etc.
- **Need POS or syntax:** plural_s_absence, past_tense_leveling, aspect_been, relativization, complementation, clefting, serial verbs, many pronoun distinctions.

**Conclusion:** It is possible to use many more grammar changes from the Ziems Multi-Value paper. Not every one can be done with simple regex (e.g. full relativization, complementation); adding a POS/syntax pipeline would allow the rest.

---

## Current status (full app integration)

- **Total features in app:** 189 (exactly the Ziems Multi-Value paper set).
- **Real transforms:** 189 (all features have real transforms).
- **No-op placeholders:** 0 (all features have real transforms) + “not yet implemented” applicability so they appear in the UI and can be selected; applying them leaves text unchanged until a real transform is added.
- **Build:** `python scripts/build_grammar_features_full.py` regenerates `shared/grammar_features.json` with exactly the paper feature list (replaces file).
