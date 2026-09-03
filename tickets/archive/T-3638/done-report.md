## Done report

Repro verdict: REPRODUCED locally. Single-run 5x was clean (matches the
addendum's expectation that this is timing-narrow), but `pytest -n 4`
(host load, matching CI's xdist parallelism) reproduced the exact CI
symptom (Err(TicketError.DuplicateId)) intermittently, with a captured
log confirming the mechanism: "id(s) {'T-0001'} present in both active
and archive" from `_load_merged`'s overlap guard.

Root cause (confirmed, not the addendum's original guess): a bare
tmp_path defaults to v2 store mode (T-1553's final-else branch), where
`archive()` dispatches to `archive_v2`, which moves each ticket
directory via `git_mv_dir` under that ticket's own PER-TICKET
`ticket_lock` only -- never `allocator_lock`, which `new_ticket`'s
allocation already holds, nor any whole-tree lock. `_load_merged`
(the allocator's taken-id read) does two SEPARATE, unlocked glob scans
(`load_all` for active, `load_archive` for archived) with nothing
serializing them against a concurrent directory rename landing between
them -- a genuine TOCTOU window (microseconds to low-milliseconds, one
git-mv subprocess), not real lock contention. The allocator's own
overlap guard (correctly conservative for a genuine T-1437-style
corruption) then aborts the whole allocation on what is actually a
perfectly healthy in-flight archive.

Fix (matches the addendum's direction 2 -- re-validate under
allocator_lock rather than erroring on collision): a bounded retry
(5 attempts, 50ms sleep between) around `_load_merged` inside
`_allocate_and_check_ticket_id`, specifically on `DuplicateId` -- a
git-mv subprocess runs on the millisecond scale, so a short, fixed
sleep (not exponential backoff; this window is expected to close in
one hop) gives the mover a real chance to finish before the next
re-read. A genuine, persistent duplicate (the T-1437 corruption case)
still surfaces as Err after exhausting the retry budget.

Evidence:
tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_archive
(0/40 failures under `pytest -n 4` after the fix, vs. reproducing
before it)
tests/test_tickets_ledger_concurrency.py full file (6/6 green)

Filed: T-3639 (renumber_one races the same allocator, same TOCTOU
family -- observed once during T-3638's own stress testing but not
reproduced densely enough this session to diagnose; out of this
ticket's declared scope, filed rather than fixed silently)

Gates: gates-native/gates-security/static chunks show no NEW findings
on src/frob/tickets/_new_renumber.py or the test file (all listed
warnings -- DOCARCH001 change-narrative, frob-arch large-file/high-
coupling/lock-identity-unresolved on this already-1800-line file --
are pre-existing, confirmed by their line numbers falling outside this
diff's added lines). ruff-check/ruff-format failures are pre-existing
repo-wide baseline (50+ unrelated files). gates-fast not re-run
standalone (same foreground-cap load the other three tickets in this
series hit on this host).

### Changed
```
 src/frob/tickets/_new_renumber.py | 54 ++++++++++++++++++++++++++++++++++++++-
 tickets/T-3638/ticket.md          |  4 ++-
 2 files changed, 56 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_archive` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 26 error(s), 4189 warning(s), 898 waived
- error-findings: ARCH102@src/frob/process/_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3628/ticket.md, DRIFT002@tests/ticket_land_suite/test_archive.py, DRIFT002@tests/ticket_land_suite/test_claim_close.py, DRIFT002@tests/ticket_land_suite/test_dirt_ownership.py, DRIFT002@tests/ticket_land_suite/test_land_core.py, DRIFT002@tests/ticket_land_suite/test_land_lock.py, DRIFT002@tests/ticket_land_suite/test_land_plan.py, DRIFT002@tests/ticket_land_suite/test_ledger_splice.py, DRIFT002@tests/ticket_land_suite/test_push.py, DRIFT002@tests/ticket_land_suite/test_release.py, DRIFT002@tests/ticket_land_suite/test_verify_intent.py, DRIFT002@tests/ticket_land_suite/test_verify_reset.py, DRIFT002@tests/ticket_land_suite/test_waive_deletion.py, DRIFT002@tests/ticket_land_suite/test_wip.py, F401@/home/logan/projects/frob/.claude/worktrees/t-3638/tests/test_ticket_land.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3638, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
