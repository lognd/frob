---
id: T-1518
title: 'move TEST016 mutation evidence off the per-land critical path: batch/nightly
  cadence, land-blocking only for security-kind'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_mutation_sweep_queue.py
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/config.py
- src/frob/_cli_parsers/_ticket/_progress.py
- tests/unit/test_mutation_sweep_queue.py
- docs/modules/tickets.md
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_mutation_sweep_queue.py
  reason: 'T-1518 batch/nightly TEST016 cadence: new sweep-queue module, land-time
    gating change, CLI flag wiring'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-1518 batch/nightly TEST016 cadence: new sweep-queue module, land-time
    gating change, CLI flag wiring'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'T-1518 batch/nightly TEST016 cadence: new sweep-queue module, land-time
    gating change, CLI flag wiring'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-1518 batch/nightly TEST016 cadence: new sweep-queue module, land-time
    gating change, CLI flag wiring'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: 'T-1518 batch/nightly TEST016 cadence: new sweep-queue module, land-time
    gating change, CLI flag wiring'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_mutation_sweep_queue.py
  reason: 'T-1518 batch/nightly TEST016 cadence: new sweep-queue module, land-time
    gating change, CLI flag wiring'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-1518 batch/nightly TEST016 cadence: new sweep-queue module, land-time
    gating change, CLI flag wiring'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-1518: --run-mutation-sweep CLI dest must be wired into AppConfig.from_external''s
    field-name tuple (WIRE001)'
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_mutation_sweep_queue.py::TestEnqueuePendingSweep::test_enqueue_persists_entry
- tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_empty_queue_is_noop
- tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_clean_finding_marks_swept_no_ticket_filed
- tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_bug_kind_confirmatory_finding_files_ticket
- tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_non_bug_confirmatory_finding_only_warns
- tests/unit/test_mutation_sweep_queue.py::TestPendingSweepCount::test_counts_only_pending_entries
designated_repro_test: null
threat: null
component: null
---
From the 2026-08-04 dev-cycle review: TEST016 (mutation evidence) is the most expensive, least incremental land stage, and its marginal per-ticket value is test-strength validation, not main-correctness. Proposal: run TEST016 per merge-queue batch drain (T-1444) or nightly over the day's landed diffs; keep it synchronous+blocking only for kind=security tickets. A batch finding files a ticket against the offending land instead of refusing it retroactively. Interacts with: T-1444 (batch boundary is the natural cadence point), the existing --skip-mutation-evidence override (today used 2x for genuine false positives T-1235/T-1439 -- a lower-frequency, higher-context batch run should also reduce false-positive pressure).