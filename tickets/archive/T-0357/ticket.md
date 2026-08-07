---
id: T-0357
title: 'coordinator land: replay worktree evidence into main .frob db on merge'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- docs/modules/tickets.md
- tests/unit/test_ticket_store.py
- .frob-release.json
- CHANGELOG.md
- pyproject.toml
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: Done report, doc entry, and test coverage for the new public replay_evidence_from_done_report
    symbol land alongside the src/frob/tickets/ change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: Done report, doc entry, and test coverage for the new public replay_evidence_from_done_report
    symbol land alongside the src/frob/tickets/ change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 version bump (0.42.0 -> 0.43.0) for the new public replay_evidence_from_done_report
    symbol
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 version bump (0.42.0 -> 0.43.0) for the new public replay_evidence_from_done_report
    symbol
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 version bump (0.42.0 -> 0.43.0) for the new public replay_evidence_from_done_report
    symbol
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 version bump (0.42.0 -> 0.43.0) for the new public replay_evidence_from_done_report
    symbol
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport::test_recovers_ids_when_structured_evidence_empty
- tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport::test_noop_when_evidence_already_present
- tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport::test_missing_evidence_when_nothing_recoverable
- tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport::test_transition_to_done_auto_replays_lost_evidence
designated_repro_test: null
threat: null
component: null
---
Evidence recorded via 'frob ticket evidence' in an implementer worktree lands in that worktree's gitignored .frob/ db, NOT tickets.md's committed ledger in a form the main-repo db recognizes. After 'git merge --no-ff' of the worktree branch, 'frob ticket close' on main fails MissingEvidence and the coordinator must re-run 'frob ticket evidence' by hand (bitten on T-0248-era lands and again T-0266). Systematize: either (a) 'frob ticket land'/merge helper replays evidence ids from the merged tickets.md Done report into the local db, or (b) evidence is persisted to the committed ledger in a db-authoritative form so a fresh clone/db reconstructs it. Wire into the coordinator-landing path so no manual re-record is ever needed.