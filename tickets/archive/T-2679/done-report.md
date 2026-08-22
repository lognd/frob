## Done report

The measured incident: a killed `frob ticket land --finish` left a ticket
`state: done` with evidence/Done-report recorded, but no land commit and no
code on main. Root cause: `_land_locked` writes the ticket's TERMINAL state
via `_land_finalize_and_close`, which commits it onto `worktree`'s branch
BEFORE `root` (main) is ever touched -- and unlike the squash-apply step
(protected by the existing T-0907 land-repair marker), that window had no
marker of its own. A kill there left the worktree's own ticket.md reading
`done` with nothing recording the fact for the machinery itself to notice.

Fix: a new `finalize-repair` marker family in `_land.py`, written
immediately before `_land_finalize_and_close` and cleared right after,
reconciled LOUDLY (naming the ticket + worktree) by
`_repair_stale_finalize_markers` at the start of every subsequent
`land()` call against the same root, for any ticket -- mirroring the
existing T-0907 marker's own scan-the-whole-directory posture. The
pre-existing T-0795 idempotent-retry path already resumes correctly from
this window (verified); this closes the missing VISIBILITY so a killed
land's terminal write is never silently invisible to the orchestrator's
own next run.

Mid-task the coordinator supplied a live T-2696 reproduction: a land
killed during post-squash `pre_commit_sweep` re-verification, well after
the squash-merge staged onto root. Investigation confirmed this window is
already covered, unchanged, by the pre-existing T-0907 marker (it brackets
the entire `_land_squash_apply` call, including that hook). Added a real
SIGKILL regression test that pauses inside `pre_commit_sweep` to reproduce
this exact window -- it passes against UNCHANGED production code,
confirming root stays clean and the next land() call repairs it.

Positive controls, both directions, all real SIGKILL (no mocked kill):
- test_sigkill_during_finalize_close_leaves_ticket_recoverable_not_a_silent_lie:
  kills mid `_land_finalize_and_close`; root's tip is unchanged, the new
  marker survives, the next land() call logs the anomaly loudly and lands
  the ticket cleanly on retry.
- test_sigkill_during_post_squash_reverification_leaves_ticket_recoverable:
  kills inside `pre_commit_sweep`, after squash-staging; root's tip is
  unchanged, the existing T-0907 marker survives and repairs on retry.
- test_normal_land_reaches_done_exactly_once_no_extra_transition: an
  ordinary uninterrupted land is unaffected -- marker written and cleared
  within the same call, `done` reached exactly once, no stray marker.

Explicitly out of scope, per the coordinator's own direction: the
DirtyMain fleet-block a killed land leaves on the shared root until a
human or a later land() call reconciles it -- a separate, larger concern
the coordinator asked be ticketed on its own rather than folded into this
targeted fix.

### Changed
```
 tickets/T-2679/ticket.md | 11 ++++++++++-
 1 file changed, 10 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_land.py::TestFinalizeRepairMarker::test_no_marker_is_a_silent_no_op` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestFinalizeRepairMarker::test_repair_logs_loudly_when_worktree_still_shows_done_but_root_does_not` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestFinalizeRepairMarker::test_repair_is_silent_when_root_already_shows_the_ticket_done` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_during_finalize_close_leaves_ticket_recoverable_not_a_silent_lie` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_normal_land_reaches_done_exactly_once_no_extra_transition` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_during_post_squash_reverification_leaves_ticket_recoverable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 47 error(s), 964 warning(s), 680 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOC006@tickets/T-2703/ticket.md, DOC006@tickets/T-2704/ticket.md, DOC006@tickets/T-2705/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2679, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE001@tests/test_ticket_land.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
