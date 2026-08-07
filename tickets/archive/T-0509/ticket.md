---
id: T-0509
title: 'INV003/INV004 calibration: 765 warnings from bare-''only'' exclusivity corpus
  -- refine patterns + markdown waiver support before burndown'
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
- tests/test_gates.py::TestInv003Gate::test_marker_naming_unknown_invariant_still_warns
- tests/test_gates.py::TestInv003Gate::test_no_exclusivity_language_is_silent
- tests/test_gates.py::TestInv003Gate::test_missing_docs_dir_is_silent
- tests/test_gates.py::TestInv003Gate::test_claim_without_verb_in_sentence_is_silent
- tests/test_gates.py::TestInv003Gate::test_claim_in_code_fence_is_silent
- tests/test_gates.py::TestInv003Gate::test_outside_spec_dirs_is_silent
- tests/test_gates.py::TestInv003Gate::test_markdown_waive_marker_with_reason_is_silent
- tests/test_gates.py::TestInv003Gate::test_markdown_waive_marker_without_reason_still_warns
- tests/test_gates.py::TestInv004Gate::test_section_with_normative_language_and_no_invariant_is_advisory
- tests/test_gates.py::TestInv004Gate::test_section_with_any_invariant_marker_is_silent
- tests/test_gates.py::TestInv004Gate::test_section_with_no_normative_language_is_silent
- tests/test_gates.py::TestInv004Gate::test_two_sections_only_flags_the_underspecified_one
- tests/test_gates.py::TestInv004Gate::test_missing_docs_dir_is_silent
- tests/test_gates.py::TestInv004Gate::test_markdown_waive_marker_with_reason_is_silent
- tests/test_gates.py::TestInv004Gate::test_claim_without_verb_in_sentence_is_silent
designated_repro_test: null
threat: null
component: null
---
T-0462/T-0452 landed WARN-severity as disclosed, but the exclusivity/normative corpora fire 765 times across docs/ -- far too noisy to burn down by hand and mostly bare-'only' prose, not genuine invariant claims. Calibrate first: require stronger claim shapes (subject+exclusivity+verb patterns, skip code fences/links/tables), add markdown-side frob:waive support so genuine-but-unprovable claims can be dispositioned, and consider scoping INV003 to spec-normative docs (docs/modules, docs/strata) rather than all docs/**.md. Then burn the residual down to zero. Scope: src/frob/gates/invariants.py, src/frob/gates/__init__.py, tests/test_gates.py, docs/modules/gates.md.