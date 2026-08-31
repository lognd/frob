---
id: T-3521
title: 'DEAD001 WARN burn-down: 23 unwired private symbols across 15 files'
state: done
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_python.py
- src/frob/arch/_abstraction.py
- src/frob/arch/_cpp.py
- src/frob/arch/_patterns.py
- src/frob/_cli_parsers/_root.py
- src/frob/app/ticket_runner/_query.py
- src/frob/gates/_docblocks_refs.py
- src/frob/gates/_fix_engine.py
- src/frob/graph/summary.py
- src/frob/lang/_common.py
- src/frob/strata/_selfconform_surface_rules.py
- src/frob/tickets/_unlanded.py
- tests/test_measure_evidence_reach.py
- tests/unit/strata/test_litmus_cwe.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/serve/_socketd.py
  reason: collides with in-progress T-3506's lease; drop from this burn-down (re-applying
    after an illegal-transition land retry)
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: T-3521's fix is comment/docstring-only plus dead-code deletion; no behavioral
    delta to reproduce
  actor: logan
  at: '2026-08-30'
  old_length: 1429
  new_length: 1728
evidence:
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_confirmed_leak_shape_done_report_plus_in_progress
- tests/test_measure_evidence_reach.py::TestMeasureEvidenceReachMain::test_runs_clean_over_a_minimal_ticket_ledger
- tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_every_catalog_entry_has_a_fixture_mapping
- tests/test_docblocks_gate.py::TestLoadParserFactoryFromRoot::test_resolves_fresh_from_root_not_the_process_import
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Remainder from T-3483's WARN family burn-down. Measured 2026-08-30 via
uv run frob check --only dead_symbols --json, filtering severity=warning
(the un-waived count -- do not conflate with the 31 total that included
already-waived findings):

DEAD001: 23 findings
  src/frob/arch/_python.py: 5
  src/frob/arch/_abstraction.py: 3
  src/frob/arch/_cpp.py: 2
  src/frob/arch/_patterns.py: 2
  src/frob/_cli_parsers/_root.py: 1
  src/frob/app/ticket_runner/_query.py: 1
  src/frob/gates/_docblocks_refs.py: 1
  src/frob/gates/_fix_engine.py: 1
  src/frob/graph/summary.py: 1
  src/frob/lang/_common.py: 1
  src/frob/serve/_socketd.py: 1
  src/frob/strata/_selfconform_surface_rules.py: 1
  src/frob/tickets/_unlanded.py: 1
  tests/test_measure_evidence_reach.py: 1
  tests/unit/strata/test_litmus_cwe.py: 1

DEAD001 is syntactic (no dynamic-reach detection) -- per this repo's own
deletion-is-a-detector-test doctrine, do NOT delete a flagged symbol
without first unwiring it and re-measuring DEAD001/WIRE001/REF002 against
the known denominator to confirm it is genuinely unreached, not reached
only through getattr/dynamic dispatch/plugin registration. Each finding
needs individual review: wire it to a real caller, delete it (after the
unwire-and-measure check), or add a reasoned frob:waive DEAD001
reason="..." if it is reached only dynamically. Promote DEAD001 WARN ->
ERROR only once the family is at genuine (unwaived) zero.

frob:no-behavior-change reason="all edits are frob:waive DEAD001 directives naming existing real callers/documented intent, one docstring correction, and deletion of two provably zero-caller symbols (_py_except_exception_type, test_litmus_cwe.py::_repo_root) -- no live code path changes behavior"