---
id: T-0882
title: 'SYS100 capability scanner: eval(/exec( needle substring-matches identifiers
  (self-match false positive)'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- strata-core/**
- design/frob.strata
- tests/unit/strata/test_conform_eval_needle.py
- src/frob/vet/_capability.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability.py
  reason: 'The SYS100 eval/exec needle the ticket describes is implemented in

    src/frob/vet/_capability.py''s plain-substring needle table (scan_file_capabilities),

    not in src/frob/strata/**. The strata self-conform scan (_selfconform.py) only

    calls into that shared vet scanner; there is no independent eval/exec needle

    inside strata itself. Fixing the false positive requires the same word-boundary

    treatment vet/_capability.py already uses for compile(/napi (T-0151/T-0019

    precedents), so this adds src/frob/vet/_capability.py to scope.

    '
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_identifier_suffix_does_not_fire_eval
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_identifier_suffix_does_not_fire_sys100
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_identifier_suffix_for_exec_does_not_fire
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_genuine_bare_eval_call_still_fires
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_genuine_bare_exec_call_still_fires
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
designated_repro_test: null
acceptance:
- text: GIVEN a scanned tree containing a function named _mutation_for_eval and no
    real eval/exec calls WHEN the SYS100 scan runs THEN no eval capability finding
    fires
  evidence:
  - tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_identifier_suffix_does_not_fire_eval
  - tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_identifier_suffix_does_not_fire_sys100
  - tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_identifier_suffix_for_exec_does_not_fire
- text: GIVEN a tree with a genuine bare eval( call WHEN the SYS100 scan runs THEN
    the finding still fires
  evidence:
  - tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_genuine_bare_eval_call_still_fires
  - tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_genuine_bare_exec_call_still_fires
- text: GIVEN the fixed scanner WHEN design/frob.strata's SYS100:eval waiver is deleted
    THEN frob sys audit stays green
  evidence:
  - tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
threat: null
component: strata
---
Found during T-0860: the strata SYS100 capability scanner's bare `eval(` needle substring-matches identifiers that merely CONTAIN "eval(" -- e.g. src/frob/mutate's `_mutation_for_eval(` function name -- producing a false "deploy uses eval" finding with zero real eval/exec builtin calls in the scanned tree. T-0860 recorded an honest waiver (design/frob.strata:519, waive "SYS100:eval" citing this ticket) rather than a false may-declaration. Fix the scanner: match `eval(`/`exec(` as call sites of the BUILTIN identifier (word-boundary / tokenized match, not raw substring), add a fixture reproducing the _mutation_for_eval self-match, then delete the waiver.