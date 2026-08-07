## Done report

T-1518: TEST016 mutation-evidence off the per-land critical path.

Changed:
- src/frob/tickets/_mutation_sweep_queue.py (new): SweepEntry/SweepQueueError
  models, SYNC_BLOCKING_KINDS={security}, enqueue_pending_sweep,
  run_pending_sweep, pending_sweep_count, _file_confirmatory_only_ticket.
  fcntl-lock-guarded .frob/mutation-sweep-queue.json, mirroring
  frob.tickets._land_queue's own T-1345 design.
- src/frob/tickets/_land.py::_check_mutation_evidence: only security-kind
  tickets still run mutation_evidence_violations synchronously and can
  refuse the land; every other kind (including bug-kind, previously also
  blocking) enqueues a deferred sweep entry instead. BUG002
  (bug_repro_violations) is unaffected -- still synchronous+ERROR-always
  for bug/security kind.
- src/frob/app/ticket_runner/_land_cmd.py: _land_drain now calls
  _run_batch_mutation_sweep(root) after draining, the natural T-1444
  cadence point; a standalone --run-mutation-sweep CLI path added for
  deployments that never call --drain.
- src/frob/app/config.py, src/frob/app/_config_external.py,
  src/frob/_cli_parsers/_ticket/_progress.py: --run-mutation-sweep flag
  plumbing (AppConfig field + argparse + external-config wiring, closing
  the WIRE001 CLI-dest check).
- docs/modules/tickets.md: updated the existing "Wired into frob ticket
  land" paragraph, added a new "Batch mutation-evidence sweep (TEST016,
  T-1518)" section.
- tests/unit/test_mutation_sweep_queue.py (new): 6 unit tests covering
  enqueue, pending_sweep_count, and run_pending_sweep's three outcomes
  (clean, bug-kind files a ticket, non-bug-kind warns only).

Evidence: 6 pytest node ids bound via the ticket evidence CLI, all
observed passing under a targeted pytest run of the new test module
(6 passed, 0 failed).

Gates: a repo-wide (not --ticket-scoped, per playbook section 6c) run of
invariant/prework/wire/test/coverage stage groups shows zero unwaived
findings against any file this ticket touched; every finding naming one
of this ticket's files carries a [waived: ...] disposition with a stated
reason (COV001 doc anchors, INV006 module-docstring waiver mirroring
_land_queue.py's precedent, WIRE001/WIRE002 test-helper waiver with
follow_up="T-1518"). Remaining unwaived findings in that run (COV006/
COV007 on tests/test_ticket_land.py, _land_cmd.py private-symbol doc
anchors, _land.py::_merge_main_into_worktree_v2) are pre-existing,
outside this ticket's scope, and do not name any file/symbol this ticket
changed.

Filed: none -- no out-of-scope work discovered.

### Changed
```
 docs/modules/tickets.md                    |  75 +++++-
 src/frob/_cli_parsers/_ticket/_progress.py |  18 ++
 src/frob/app/_config_external.py           |   2 +
 src/frob/app/config.py                     |   6 +
 src/frob/app/ticket_runner/_land_cmd.py    |  49 ++++
 src/frob/tickets/_land.py                  |  82 ++++--
 src/frob/tickets/_mutation_sweep_queue.py  | 399 +++++++++++++++++++++++++++++
 tests/unit/test_mutation_sweep_queue.py    | 179 +++++++++++++
 tickets.md                                 |  68 ++++-
 9 files changed, 843 insertions(+), 35 deletions(-)
```

### Evidence
- `tests/unit/test_mutation_sweep_queue.py::TestEnqueuePendingSweep::test_enqueue_persists_entry` (pytest node id, verified passing when recorded)
- `tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_empty_queue_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_clean_finding_marks_swept_no_ticket_filed` (pytest node id, verified passing when recorded)
- `tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_bug_kind_confirmatory_finding_files_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_non_bug_confirmatory_finding_only_warns` (pytest node id, verified passing when recorded)
- `tests/unit/test_mutation_sweep_queue.py::TestPendingSweepCount::test_counts_only_pending_entries` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 696 warning(s), 786 waived
- error-findings: none (measured, zero errors)
