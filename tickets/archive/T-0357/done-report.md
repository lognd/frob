## Done report

Added frob.tickets.replay_evidence_from_done_report, the inverse of
render_evidence_block: it parses the rendered "### Evidence" section of a
ticket's Done report and, when the ticket's structured evidence: field is
empty, writes the recovered ids back into it (idempotent, ledger-locked).
Wired automatically into transition(root, ticket_id, DONE): a ticket
arriving with empty evidence now gets a best-effort recovery attempt from
its own committed Done report text before the ordinary MissingEvidence
rejection fires. This closes the coordinator-land gap where a hand
`git merge --no-ff` of a worktree branch (bypassing `frob ticket land`'s
ledger splice) could leave the Done report prose intact while the
structured evidence field was lost, forcing a manual `frob ticket
evidence` re-record on main (T-0248/T-0266 incidents). Recovered ids are
not re-validated against a fresh collection/pass run; frob check's
COV003/TEST001 gates still catch a stale or fabricated id independently.

### Changed
```
 .frob-release.json              |   3 +-
 CHANGELOG.md                    |  18 +++++++
 docs/modules/tickets.md         |  13 +++++
 pyproject.toml                  |   2 +-
 src/frob/tickets/__init__.py    | 102 ++++++++++++++++++++++++++++++++++++++++
 tests/unit/test_ticket_store.py |  68 +++++++++++++++++++++++++++
 tickets.md                      |  34 +++++++++++++-
 uv.lock                         |   2 +-
 8 files changed, 237 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport::test_recovers_ids_when_structured_evidence_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport::test_noop_when_evidence_already_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport::test_missing_evidence_when_nothing_recoverable` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport::test_transition_to_done_auto_replays_lost_evidence` (pytest node id, verified passing when recorded)
