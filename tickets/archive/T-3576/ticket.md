---
id: T-3576
title: teach WIRE001 call-graph analyzer to resolve multiprocessing.Process target=
  kwarg references
state: done
kind: feature
origin: agent
created: '2026-08-31'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
- tests/unit/test_wire001_multiprocessing_target.py
- tests/unit/test_fix_engine_journal.py
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_wire001_multiprocessing_target.py
  reason: regression fixtures locking WIRE001's already-correct multiprocessing.Process(target=)
    resolution; removes the now-obsolete waiver from the real file
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tests/unit/test_fix_engine_journal.py
  reason: regression fixtures locking WIRE001's already-correct multiprocessing.Process(target=)
    resolution; removes the now-obsolete waiver from the real file
  actor: logan
  at: '2026-08-31'
- op: add
  glob: design/frob.strata
  reason: declare fs.write/exec capability for the new fixture test file, needed by
    the strata self-conformance gate
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: bump testsuite exec/fs.write ratchet ceilings by 1 for the new fixture file
  actor: logan
  at: '2026-08-31'
evidence:
- tests/unit/test_wire001_multiprocessing_target.py::TestWire001MultiprocessingProcessTarget::test_function_passed_as_process_target_kwarg_is_not_flagged
- tests/unit/test_wire001_multiprocessing_target.py::TestWire001MultiprocessingProcessTarget::test_function_passed_as_context_process_target_kwarg_is_not_flagged
- tests/unit/test_wire001_multiprocessing_target.py::TestWire001MultiprocessingProcessTarget::test_function_with_no_process_target_caller_anywhere_still_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3558 verified tests/unit/test_fix_engine_journal.py's frob:waive WIRE001 on _write_journal_and_block is genuinely load-bearing: the function is wired via multiprocessing.Process's own target= kwarg in TestAbandonedAutofixJournalSigkillSubprocess.test_sigkilled_journal_writer_is_detected_and_refused, but WIRE001's call-graph analyzer does not resolve a target= reference the way it resolves a direct call, so the analyzer flags it as unwired without this waiver. Real fix: teach the analyzer to follow multiprocessing.Process(target=...)/multiprocessing.pool's equivalent kwarg the same way it already resolves direct calls (or an equivalent explicit annotation convention), so this class of genuinely-wired-but-indirectly-invoked callable stops needing a manual waiver. Re-pointing the waiver's follow_up from T-3558 to this ticket (T-3558 itself did no code change, only verification + this re-point, and cannot remain the live tracker once closed).