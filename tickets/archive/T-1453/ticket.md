---
id: T-1453
title: 'strata: migrate design/frob.strata''s may grants to scoped via globs'
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
- src/frob/strata/_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: 'The T-1450 SYS101 per-via rewrite of src/frob/strata/_selfconform.py

    relocated the pre-existing "frob:waive PERF004 reason=distinct small

    per-node diff set, not repeated" comment from the old whole-node loop

    (deleted by that rewrite) onto the two new loops inside

    _stale_design_violations_for_node (the via-less fallback loop and the

    per-may_grants loop), preserving the same waived concern at its new call

    sites. That relocation trips T-1453''s committed-waive-deletion land

    check because src/frob/strata/_selfconform.py sits outside T-1453''s

    declared scope (design/frob.strata only), even though the deleting

    commit is T-1450''s own in-scope work on the shared branch. Adding this

    file to T-1453''s scope acknowledges the shared-branch history rather

    than re-scoping T-1450 after the fact.

    '
  actor: logan
  at: '2026-08-03'
evidence:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
designated_repro_test: null
threat: null
component: null
---
T-1440 parent: migrate design/frob.strata's existing whole-node `may`
grants to scoped `via` grants now that the grammar/join support it.
T-1440 deliberately does NOT touch design/frob.strata's own grants (the
repo must stay green with via-less grants throughout T-1440's own
landing) -- this is that follow-up. Plan (per T-1440's migration note,
docs/strata/surface.md#may-scope): use the mutation-audit scanner's
existing per-file observation data (`_mutation_audit.py`'s
`_observed_raw_kinds_by_node`/`raw_by_node`, already computed per node
during the baseline scan) to find, for each declared `may` atom on each
broad node (testsuite: code tests/**, stratamod, etc.), the real file
set that actually exercises that kind, and narrow the grant's `via` down
to it. Verify with `frob sys audit`/`check_capability_conformance`
staying green (no new SYS100) after each node's migration -- migrate
one broad node at a time, not a single flag-day commit, to keep any
break bisectable.