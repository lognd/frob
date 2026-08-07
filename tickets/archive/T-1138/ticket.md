---
id: T-1138
title: 'gates --fix Tier-A batch 1: directive-form rewrite + unique anchor-slug correction
  + TICK002 renumber'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- tests/test_gates.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: 'This ticket adds real new public symbols to frob.gates (FixApplied,

    apply_tier_a_fixes, fix_doc002_unique_slug, fix_doc007_dotted_form,

    fix_tick002_renumber). SYS104 is now mandatory (coordinator directive,

    T-1113''s flip): the gates node in design/frob.strata needs its

    interface= attrs updated in the same land or main goes red. Adding it

    so that mechanical upkeep can land alongside the new symbols.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean
- tests/test_gates.py::TestFixEngineTierA::test_doc007_already_dotted_is_a_no_op
- tests/test_gates.py::TestFixEngineTierA::test_doc002_unique_fuzzy_candidate_rewritten_and_reverifies_clean
- tests/test_gates.py::TestFixEngineTierA::test_doc002_ambiguous_candidates_stay_unfixed
- tests/test_gates.py::TestFixEngineTierA::test_doc002_zero_candidates_stay_unfixed
- tests/test_gates.py::TestFixEngineTierA::test_tick002_renumbers_draft_and_reverifies_clean
- tests/test_gates.py::TestFixEngineTierA::test_tick002_off_default_branch_is_a_no_op
designated_repro_test: null
acceptance:
- text: 'GIVEN a frob:tests edge in pytest :: form WHEN --fix runs THEN it is rewritten
    to the dotted Class.method form and DRIFT002/DOC007 re-verify clean'
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean
  - tests/test_gates.py::TestFixEngineTierA::test_doc007_already_dotted_is_a_no_op
- text: GIVEN a frob:doc/frob:tests anchor whose slug mismatches but fuzzy-matches
    exactly one real heading slug in the target doc THEN --fix rewrites it to that
    slug; zero or multiple candidates stay unfixed with an assisted fix-it
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_doc002_unique_fuzzy_candidate_rewritten_and_reverifies_clean
  - tests/test_gates.py::TestFixEngineTierA::test_doc002_ambiguous_candidates_stay_unfixed
  - tests/test_gates.py::TestFixEngineTierA::test_doc002_zero_candidates_stay_unfixed
- text: GIVEN a TICK002 draft-survived-onto-main finding THEN --fix performs the renumber
    it already prescribes, including prose-reference rewrite once T-1125 lands
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_tick002_renumbers_draft_and_reverifies_clean
  - tests/test_gates.py::TestFixEngineTierA::test_tick002_off_default_branch_is_a_no_op
threat: null
component: null
---
First concrete slice of the T-1137 fix engine, restricted to the three fix classes with unambiguous deterministic rewrites and repeated main-redding history (DRIFT002 dotted-form x4+, T-0602 slug incident, TICK002 this wave). Ship behind --fix; no waiver insertion; each applied fix re-runs its gate in-process.