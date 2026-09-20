---
id: T-4556
title: 'T-3612 follow-up: renumber, promote and archive still route through the narrowed
  LandInProgress probe; their multi-file writes need the whole-land exclusion back'
state: done
kind: bug
origin: agent
created: '2026-09-17'
priority: medium
parent: T-3611
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/__init__.py
- src/frob/tickets/_leases.py
- tests/unit/test_land_in_progress_window.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_land_in_progress_window.py::TestWholeLandVerbClassification::test_renumber_refused_while_only_land_lock_held
- tests/unit/test_land_in_progress_window.py::TestWholeLandVerbClassification::test_splice_only_verb_allowed_while_only_land_lock_held
- tests/unit/test_land_in_progress_window.py::TestDispatchLayerWholeLandClassification::test_renumber_exits_while_only_land_lock_held
- tests/unit/test_land_in_progress_window.py::TestDispatchLayerWholeLandClassification::test_evidence_proceeds_while_only_land_lock_held
designated_repro_test: null
acceptance:
- text: GIVEN a land in progress (land.lock held, tickets.lock free) WHEN frob ticket
    renumber, promote, archive or migrate is invoked THEN it is refused naming the
    land, while new/drop/body/scope/fail/evidence/done-report/accept succeed
  evidence:
  - tests/unit/test_land_in_progress_window.py::TestWholeLandVerbClassification::test_renumber_refused_while_only_land_lock_held
  - tests/unit/test_land_in_progress_window.py::TestWholeLandVerbClassification::test_splice_only_verb_allowed_while_only_land_lock_held
  - tests/unit/test_land_in_progress_window.py::TestDispatchLayerWholeLandClassification::test_renumber_exits_while_only_land_lock_held
  - tests/unit/test_land_in_progress_window.py::TestDispatchLayerWholeLandClassification::test_evidence_proceeds_while_only_land_lock_held
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3612 narrowed refuse_if_land_in_progress to the tickets.lock splice window for all callers; the dispatch layer in src/frob/app/ticket_runner/__init__.py routes renumber/promote/archive through the same probe, and those verbs rewrite many ticket files without a single lock, so they can now interleave with a land's out-of-tree compose. Add a verb classification (splice-only vs whole-land) at the dispatch layer and tests for both classes.