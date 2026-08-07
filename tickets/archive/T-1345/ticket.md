---
id: T-1345
title: 'Merge queue: agents enqueue verified branches, one drainer merges onto main'
state: done
kind: feature
origin: human
created: '2026-07-31'
priority: critical
parent: T-1344
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- docs/guides/agent-playbook.md
- tests/unit/test_land_queue.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_queue.py
  reason: test file for the new _land_queue module
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/test_land_queue.py::TestDrainNext::test_second_entry_still_drains_after_first_failure
- tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_returns_queued_entry
- tests/unit/test_land_queue.py::TestDrainNext::test_failed_land_rejected_back_not_retried
- tests/unit/test_land_queue.py::TestDrainNext::test_failed_entry_is_not_redrained
- tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_persists_across_calls
- tests/unit/test_land_queue.py::TestEnqueue::test_duplicate_enqueue_refused
- tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_after_landed_is_allowed
- tests/unit/test_land_queue.py::TestQueueStatus::test_empty_queue_is_empty_tuple
- tests/unit/test_land_queue.py::TestDrainNext::test_empty_queue_returns_none
- tests/unit/test_land_queue.py::TestDrainNext::test_drains_fifo_order
- tests/unit/test_land_queue.py::TestDrainNext::test_successful_land_marks_entry_landed
- tests/unit/test_land_queue.py::TestStoreCorrupt::test_corrupt_queue_file_errors
designated_repro_test: null
acceptance:
- text: given two agents landing at once, when both enqueue, then both land in sequence
    with neither refused for DirtyMain and neither writing to main directly
  evidence:
  - tests/unit/test_land_queue.py::TestDrainNext::test_second_entry_still_drains_after_first_failure
  - tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_returns_queued_entry
- text: given a queued branch that no longer merges cleanly after an earlier entry
    lands, when the drainer reaches it, then it is handled by a declared policy rather
    than silently dropped
  evidence:
  - tests/unit/test_land_queue.py::TestDrainNext::test_failed_land_rejected_back_not_retried
  - tests/unit/test_land_queue.py::TestDrainNext::test_failed_entry_is_not_redrained
threat: null
component: tickets
---
Leaf of T-1344. THE highest-leverage item: today every agent landed onto one shared main checkout, so lands serialize by collision-and-retry rather than by design.

Observed failures this shape caused: a DirtyMain refusal costing a full retry cycle (T-1336); an agent committing a SIBLING's uncommitted ledger churn to main twice just to clear DirtyMain (T-1337) -- inert that time, but the shape lets one agent commit another's half-finished work; and repeated multi-minute waits.

PROPOSAL: <!-- frob:waive DOC006 reason="design proposal naming a CLI flag that does not exist yet -- disclosed future work" -->"frob ticket land --queue" enqueues a verified worktree branch and returns immediately. A single serialized drainer merges queued branches onto main one at a time, running the post-merge gate check per merge. Agents then NEVER write to main directly.

MEASURED EVIDENCE (2026-07-31, mined from .frob/telemetry.jsonl, 12,300 records) -- this is now the single most expensive operation in the tool:
  ticket land   13.38 h total over 752 calls   (mean 78s when it succeeds)
    succeeded   484 calls  10.46 h
    FAILED      268 calls   2.92 h  <-- 36% failure rate, pure waste
  For comparison: ALL `frob check` invocations combined cost 6.82 h over 1116 calls.
  `ticket land` alone is ~60% of all frob wall-clock in the corpus, and its
  failures alone (2.92 h) cost more than any other subcommand's total.
The dominant failure mode is DirtyMain contention between concurrent agents --
exactly what a merge queue eliminates by construction. This ticket is therefore
the highest-value speed work in the repo, ahead of any gate optimization.

Design questions to answer in the ticket, not assume:
- Where does the queue live so it survives a crashed drainer (a git ref? a file under .frob/ with a lock?).
- What happens when a queued branch no longer merges cleanly after an earlier queue entry lands -- reject back to the agent, or auto-rebase and re-verify?
- The gate check must run POST-merge to be meaningful; that is what makes throughput depend on the memoization leaf.
- Does this subsume the archived T-1058 stale-worktree-base hazard? If the drainer always merges current main, a stale base becomes detectable at enqueue.

Preserve the existing LAND-PROOF contract: whatever the agent gets back must still let it prove commit + is_ancestor_of_main + state_on_main, or the verification discipline this repo depends on breaks.