## Done report

Changed:
- src/frob/tickets/_models.py::Ticket.land_commit (new field)
- src/frob/tickets/_land_squash.py::_record_land_commit (new)
- src/frob/tickets/_land_squash.py::_finish_real_land_report (new, split from _land_squash_apply_finish to clear ARCH001)
- src/frob/tickets/_land_squash.py::_land_squash_apply_finish (calls _finish_real_land_report)
- src/frob/tickets/_land.py::_land_plan_finalize_drafts (now stamps land_commit=merge_commit onto each finalized ticket, in-memory, before the finalize commit)
- src/frob/tickets/_land.py::_land_plan_merge_and_finalize (threads merge_commit into _land_plan_finalize_drafts)
- src/frob/tickets/_land_ledger_merge.py::_overlay_landed_ticket (carries land_commit forward across a same-worktree retry's tie-break, so it is never silently erased)
- src/frob/app/ticket_runner/_lifecycle.py::_find_landing_commit (now reads Ticket.land_commit, no git log --grep)
- scripts/verify_lands.py::load_land_commit (new), main() (accepts a ticket id alongside a sha)
- docs/guides/coordinator-scripts.md, docs/modules/tickets-landing.md (updated)
- docs/design/registry/capability-via-ratchet.lock.json (tickets_ledger::fs.write ratchet bumped 16 -> 17)

Evidence:
- tests/test_ticket_land.py::TestRecordLandCommit::test_records_land_commit_field_in_a_follow_up_commit (--accepts 0, DESIGNATED REPRO -- FAILED_AT_PARENT confirmed against 60394a1b252d086068832dd24c299ad8ce6e9eb7, the test-only commit before the fix)
- tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_ticket_id_argument_resolves_via_land_commit (--accepts 1, must-still-pass SHA control + ticket-id resolution)
- tests/test_ticket_land.py::TestRecordLandCommit::test_plan_land_finalized_ticket_is_resolvable_by_ticket_id (--accepts 2, the --plan discriminator: asserts the finalize commit subject is NOT matchable by the old `land T-####` grep pattern, and that land_commit resolves anyway)
- tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_never_landed_ticket_id_refused_distinguishably_from_a_typo_sha (--accepts 3)
- tests/unit/test_coordinator_scripts.py::TestLoadLandCommit (3 methods, unit coverage for the new resolver)
- Full `tests/test_ticket_land.py` run (9925 lines, 279+ tests): only 4 failures, all independently confirmed PRE-EXISTING on main (test_refuses_on_dirty_main, TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice, TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses, TestUvLockSync::test_dirty_lock_with_other_change_still_refuses -- reproduced against a pristine `git worktree add --detach main` checkout before any of this ticket's edits)
- Full `tests/test_ticket_leases.py` run: 132/132 pass
- `tests/test_evidence_integrity.py`, `tests/test_ticket_work_and_land_finish.py`, `tests/test_tickets_collision.py`, `tests/unit/test_land_squash_residue_reclaim.py`: 136/136 pass
- `frob check --only lint/static/gates-native/gates-security/test --ticket T-2220`: every remaining ERROR-level finding independently confirmed pre-existing/unrelated (untouched files: src/frob/lang/_nodes.py, tests/test_ticket_work_and_land_finish.py, scripts/fleet_status.py, src/frob/app/ticket_runner/_land_cmd.py, src/frob/app/ticket_runner/_rapid_sweep.py, tickets.md backlog-rot TICK004/TICK006, pre-existing import cycles reproduced identically on a pristine main checkout)
- `uv run ty check src/frob/tickets/_land_squash.py`: clean after the frozenset[str] annotation fix

Filed: none (all follow-up work was in-scope drift-repair, folded into this ticket via `frob ticket scope --add` with citable reasons: src/frob/tickets/_land_squash.py, src/frob/tickets/_land_ledger_merge.py, docs/design/registry/capability-via-ratchet.lock.json, plus the three test files this ticket's own evidence lives in)

Gates: `frob check --only lint/static/gates-native/gates-security/test --ticket T-2220` clean of new findings (confirmed error-by-error against a pristine main checkout). `frob check --land-parity` could not complete under this session's WSL contention (repeatedly deferred/timed out on the `static` stage group inside its internal 300s budget across 3 attempts) -- NOT proof of a clean tree by the tool's own contract, but every family it would have run was independently verified clean via the `--only` stage checks above, including `--only static` itself.

## Design note: why a follow-up commit, not the squash commit itself

`land_commit` cannot be baked into the commit it names (a commit's hash is
a function of its own content, so it cannot contain its own future hash).
For the per-ticket `land <id>` path, `_record_land_commit` writes the field
in a small commit made immediately after the squash-apply commit, still
inside the same `land()` call -- `root`'s tip after a real land is now one
commit ahead of `LandReport.commit_sha` (unchanged: still names the
code-carrying commit). For `land --plan`, no such problem exists:
`merge_commit` is already a prior, real commit by the time the finalize
step runs, so it is stamped directly into the finalize commit's own
content with no follow-up needed.

This shifted two pre-existing tests' assumptions (`git rev-parse HEAD`
after a land now differs from `LandReport.commit_sha` by one commit) --
both updated to assert against the correct commit
(`TestReleaseBumpQuartetAtomicity::test_manifest_version_written_same_step_as_pyproject`,
`TestUvLockSync::test_bump_then_lock_synced_in_commit`), and the T-1001
absorption retry test's own "same commit" assertion was similarly
corrected to compare against root's actual post-land tip rather than the
squash-only sha.

### Changed
```
 .../registry/capability-via-ratchet.lock.json      |   6 +-
 docs/guides/coordinator-scripts.md                 |  35 ++++-
 docs/modules/tickets-landing.md                    |  38 +++++-
 scripts/verify_lands.py                            |  75 ++++++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |  45 +++----
 src/frob/tickets/_land.py                          |  48 ++++++-
 src/frob/tickets/_land_ledger_merge.py             |  20 ++-
 src/frob/tickets/_land_squash.py                   | 128 +++++++++++++++++++
 src/frob/tickets/_models.py                        |  16 +++
 tests/test_ticket_land.py                          | 142 ++++++++++++++++++++-
 tests/test_ticket_leases.py                        |  16 ++-
 tests/unit/test_coordinator_scripts.py             | 100 +++++++++++++++
 tickets/T-2220/ticket.md                           |  79 +++++++++++-
 13 files changed, 685 insertions(+), 63 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestRecordLandCommit::test_records_land_commit_field_in_a_follow_up_commit` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_ticket_id_argument_resolves_via_land_commit` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRecordLandCommit::test_plan_land_finalized_ticket_is_resolvable_by_ticket_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_never_landed_ticket_id_refused_distinguishably_from_a_typo_sha` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV001@src/frob/scaffold/_skills_sync.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1335, COV003@tickets/T-1353, COV003@tickets/T-1362, COV003@tickets/T-1363, COV003@tickets/T-1373, COV003@tickets/T-1397, COV003@tickets/T-1426, COV003@tickets/T-1433, COV003@tickets/T-1526, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC002@src/frob/scaffold/_skills_sync.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2220/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2220/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2220, RENDER001@src/frob/scaffold/_skills_sync.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
