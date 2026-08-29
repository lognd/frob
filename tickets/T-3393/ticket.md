---
id: T-3393
title: Fix DOC011/DOCENUM001 stale doc references and PERF004 loop-sort findings
state: done
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/gates.md
- src/frob/lang/_support.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets.md
  reason: T-3358 has an active in-progress lease on this file; DOC011 fix dropped
    from this ticket's scope to avoid lease collision
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: .claude/hooks/frob-suggest.py
  reason: T-3389 (Series EQ) holds a live in-progress lease on this file; PERF004
    fix here deferred to avoid a cross-ticket collision
  actor: logan
  at: '2026-08-29'
evidence:
- tests/test_lang_support.py::TestPackageAudit::test_every_measured_package_is_registered
- tests/test_lang_support.py::TestPackageAudit::test_must_fire_unregistered_language_branching
- tests/test_lang_support.py::TestPackageAudit::test_must_stay_quiet_agnostic_package
- tests/test_lang_support.py::TestPackageAudit::test_registered_package_never_flagged_even_with_literals
- tests/test_lang_support.py::TestPackageAudit::test_real_repo_source_tree_is_fully_registered
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
gate:LARGE ER slice: DOC011 (stale T-draft-ad5e921b citation in docs/modules/tickets.md, now T-3360), DOCENUM001 (docs/modules/gates.md rule-catalog enumerate list omitted TDD001/VERSION001/VMOD001), and two PERF004 sort-in-loop findings (.claude/hooks/frob-suggest.py, src/frob/lang/_support.py -- both waived with per-iteration-varies-input reasoning since a hoist is not correct there).