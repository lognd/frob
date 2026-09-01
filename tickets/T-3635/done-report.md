## Done report

Repointed 253 self-referential frob:tests directives (DRIFT002) across 13 tests/ticket_land_suite/*.py files -- each moved test's own self-citation still pointed at its old tests/test_ticket_land.py location, only cross-file citations were fixed at split time. Pruned the now-fully-unused import block tests/test_ticket_land.py's shim left behind (60 ruff F401 errors that were blinding all 3 CI legs). Waived 2 pre-existing DOC006 findings in tickets/T-3628/ticket.md (planned-but-not-built module names, unrelated to this split). Verified: ruff check src tests clean repo-wide; tests/test_ticket_land.py + tests/ticket_land_suite/ full suite green (345/345).

### Changed
```
 tests/test_ticket_land.py                      | 59 ----------------
 tests/ticket_land_suite/test_archive.py        |  2 +-
 tests/ticket_land_suite/test_claim_close.py    | 94 +++++++++++++-------------
 tests/ticket_land_suite/test_dirt_ownership.py | 36 +++++-----
 tests/ticket_land_suite/test_land_core.py      | 46 ++++++-------
 tests/ticket_land_suite/test_land_lock.py      | 46 ++++++-------
 tests/ticket_land_suite/test_land_plan.py      | 42 ++++++------
 tests/ticket_land_suite/test_ledger_splice.py  | 46 ++++++-------
 tests/ticket_land_suite/test_push.py           | 32 ++++-----
 tests/ticket_land_suite/test_release.py        | 64 +++++++++---------
 tests/ticket_land_suite/test_verify_intent.py  | 32 ++++-----
 tests/ticket_land_suite/test_verify_reset.py   | 60 ++++++++--------
 tests/ticket_land_suite/test_waive_deletion.py |  4 +-
 tests/ticket_land_suite/test_wip.py            |  2 +-
 tickets/T-3628/ticket.md                       |  4 +-
 tickets/T-3635/ticket.md                       | 16 ++++-
 16 files changed, 269 insertions(+), 316 deletions(-)
```

### Evidence
- `tests/ticket_land_suite/test_archive.py::TestArchiveV2::test_v2_draft_survives_a_concurrent_worktree_restore` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_matching_claims_land_succeeds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 13 error(s), 4508 warning(s), 896 waived
- error-findings: ARCH102@src/frob/process/_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT002@tests/unit/arch_suite/test_complexity.py, DRIFT002@tests/unit/arch_suite/test_misc.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3635, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
