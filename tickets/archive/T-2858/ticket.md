---
id: T-2858
title: 'Main red: DRIFT002/DOC006/COV001/TEST001 outside T-2855 scope (tickets-data-storage.md,
  test005 audit, callgraph.py, _multifile.py)'
state: done
kind: bug
origin: human
created: '2026-08-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-data-storage.md
- docs/audits/test005-zero-classification-t1418.md
- src/frob/graph/callgraph.py
- src/frob/strata/_multifile.py
evidence_scope:
- tests/unit/strata/test_fragments.py
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 escape hatch: this ticket closes as duplicate-of-fixed with no code
    change of its own'
  actor: logan
  at: '2026-08-22'
  old_length: 1383
  new_length: 1856
evidence:
- tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_declared_atom_still_works
- tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_undeclared_atom_refuses_closed
- tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_fresh_insert_raises_at_runtime
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 847b352eb4906a553be19eae6557fde67496fd6e
---
Found while re-measuring main's red-build state for T-2855 (post-land sweep regression from T-2846's rust split). These 4 error-severity findings are a SEPARATE root cause from T-2846/T-2855's rust-split fallout -- confirmed by file: none of these paths are in T-2855's scope (frob-core/src/*.rs, docs/modules/dup.md, docs/modules/dup-sota-survey.md, tests/unit/test_dup_core.py, tests/test_arch_near_duplicate_native.py) or attributable to T-2846's commit. Measured via unbudgeted 'frob check --json --ticket <id>' (gate-summary present): DRIFT002 x4 on docs/modules/tickets-data-storage.md (describes edges to src/frob/tickets/_store.py::migrate_to_ledger/migrate_v1_to_v2/_migrate_one/_split_done_report_from_ticket no longer resolve -- looks like the same T-2695 v1/v2-migration-split-residue class T-2822's own waiver text names, i.e. a doc left pointing at pre-split _store.py after functions moved to _store_migrate.py), DOC006 x1 on docs/audits/test005-zero-classification-t1418.md (anchor #6d-test005-reads-coveragexml-and-make-coverage-delete does not resolve), COV001 x1 on src/frob/graph/callgraph.py::build_call_graph (missing frob:doc edge), TEST001 x1 on src/frob/strata/_multifile.py::SealedGrantSet.from_root_node (missing unit test). Filed as one ticket per the playbook's found-work-outside-scope rule rather than silently expanding T-2855's scope; not fixed here.

<!-- frob:waive BUG002 reason="This ticket closes as duplicate-of-fixed: all 4 declared findings were already resolved by T-2801's landed fix (f60eb5404c7480775e98401b1aaf54ad074ef219), confirmed by direct re-measurement in this ticket's own worktree. No code change of this ticket's own exists to bind a fail-then-pass repro against; the bound evidence is confirmatory (demonstrates the already-fixed symbols still work), not a reproduction of a defect fixed here." -->