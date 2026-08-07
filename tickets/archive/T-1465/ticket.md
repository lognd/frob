---
id: T-1465
title: clear T-1360/T-1462 land residue
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability_core.py
- tests/test_capability_registry.py
- src/frob/app/telemetry.py
- src/frob/vet/_capability.py
- design/frob.strata
- frob.lock
- docs/guides/agentic-time-profiling.md
- docs/modules/stats.md
- tests/test_vet.py
- tests/conftest.py
- tests/unit/test_conftest_stackdump.py
- pyproject.toml
- Makefile
- tests/unit/test_makefile_coverage.py
- tests/test_ticket_leases.py
- src/frob/graph/dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: SYS104 interface metadata + ack lock edits, plus AFFECT001-waived doc targets
    need to be gate:SCOPE-visible
  actor: logan
  at: '2026-08-02'
- op: add
  glob: frob.lock
  reason: SYS104 interface metadata + ack lock edits, plus AFFECT001-waived doc targets
    need to be gate:SCOPE-visible
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/guides/agentic-time-profiling.md
  reason: SYS104 interface metadata + ack lock edits, plus AFFECT001-waived doc targets
    need to be gate:SCOPE-visible
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/modules/stats.md
  reason: SYS104 interface metadata + ack lock edits, plus AFFECT001-waived doc targets
    need to be gate:SCOPE-visible
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_vet.py
  reason: new mutation-killing unit test for _operation_entry_matches fallthrough
    (TEST016 remedy)
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/conftest.py
  reason: the branch's post-merge fix commits touch these files (T-1433 instrumentation
    + coordinator-requested residue findings); the deletion filter needs them in the
    landing ticket's scope -- the conftest frob:waive minus-lines are fmt rewraps,
    not deletions
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: the branch's post-merge fix commits touch these files (T-1433 instrumentation
    + coordinator-requested residue findings); the deletion filter needs them in the
    landing ticket's scope -- the conftest frob:waive minus-lines are fmt rewraps,
    not deletions
  actor: logan
  at: '2026-08-02'
- op: add
  glob: pyproject.toml
  reason: the branch's post-merge fix commits touch these files (T-1433 instrumentation
    + coordinator-requested residue findings); the deletion filter needs them in the
    landing ticket's scope -- the conftest frob:waive minus-lines are fmt rewraps,
    not deletions
  actor: logan
  at: '2026-08-02'
- op: add
  glob: Makefile
  reason: the branch's post-merge fix commits touch these files (T-1433 instrumentation
    + coordinator-requested residue findings); the deletion filter needs them in the
    landing ticket's scope -- the conftest frob:waive minus-lines are fmt rewraps,
    not deletions
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: the branch's post-merge fix commits touch these files (T-1433 instrumentation
    + coordinator-requested residue findings); the deletion filter needs them in the
    landing ticket's scope -- the conftest frob:waive minus-lines are fmt rewraps,
    not deletions
  actor: logan
  at: '2026-08-02'
- op: add
  glob: design/frob.strata
  reason: the branch's post-merge fix commits touch these files (T-1433 instrumentation
    + coordinator-requested residue findings); the deletion filter needs them in the
    landing ticket's scope -- the conftest frob:waive minus-lines are fmt rewraps,
    not deletions
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_ticket_leases.py
  reason: the branch's post-merge fix commits touch these files (T-1433 instrumentation
    + coordinator-requested residue findings); the deletion filter needs them in the
    landing ticket's scope -- the conftest frob:waive minus-lines are fmt rewraps,
    not deletions
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/graph/dsl.py
  reason: the branch's post-merge fix commits touch these files (T-1433 instrumentation
    + coordinator-requested residue findings); the deletion filter needs them in the
    landing ticket's scope -- the conftest frob:waive minus-lines are fmt rewraps,
    not deletions
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_telemetry.py::test_timed_call_maps_bare_system_exit_to_zero
- tests/test_telemetry.py::test_timed_call_maps_non_int_system_exit_code_to_one
- tests/test_telemetry.py::test_timed_call_records_event_and_returns_value
- tests/test_telemetry.py::test_timed_call_records_nonzero_exit_on_system_exit
- tests/test_telemetry.py::test_usage_report_aggregates_time_and_failures
- tests/test_telemetry.py::test_usage_report_counts_fast_exit1
- tests/test_telemetry.py::test_usage_report_counts_redundant_reruns
- tests/test_telemetry.py::test_usage_report_empty_corpus_is_all_zero
- tests/test_capability_registry.py::test_fire_fixture_names_a_registry_entry
- tests/test_vet.py::TestOperationEntryMatchesFallthrough::test_no_needles_and_not_bare_compile_returns_false
designated_repro_test: null
threat: null
component: null
---
main has 4 live errors post T-1360/T-1462 land: (a) src/frob/vet/_capability_core.py:589 ty invalid-return-type -- function can implicitly return None but declares bool; (b) tests/test_capability_registry.py:339 imports _SPECIAL_CHECKS from frob.vet._capability but T-1462 split moved it; (c) src/frob/app/telemetry.py ARCH001 x2: timed_call (64 lines) and usage_report (82 lines) too long, need helper extraction.