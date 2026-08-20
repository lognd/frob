## Done report

Three measured incidents, one session: T-2696's own killed land, a `frob
ticket new` whose ledger commit lost a race, and a `frob ticket scope`
mirror-write that lost its commit. All three share ONE shape: a process
killed strictly between `git add` and `git commit` strands the shared
root DIRTY, and DirtyMain then correctly (by design) blocks every other
agent's land/ledger-write until a human adjudicates by hand. In all three
cases the staged content was already complete and correct -- the WRITE
(write_ticket/set_scope/etc.) finished before the git bookkeeping was
ever interrupted -- so the fix is reconciliation, not prevention, exactly
as T-2679's finalize-repair marker modeled.

Two distinct call sites cover the two source pipelines:

1. `src/frob/tickets/_leases.py`: `_add_and_commit_tickets_md` is the
   SINGLE choke point every non-land ledger-mutating verb (new, scope,
   drop, fail, done-report, evidence, close, requeue, block, priority,
   kind, ...) already funnels through (T-1615). A new
   `ledger-commit-repair` marker family brackets its add+commit exactly
   like T-0907/T-2679's own land markers: written before `git add`,
   cleared in a `finally` right after. `_repair_stale_ledger_commit_
   markers` reconciles any leftover marker at the START of every
   subsequent call to this same function, for any ticket -- if root's
   tip is unchanged since the crash and the marker's own recorded
   pathspecs are still dirty, it re-attempts the IDENTICAL, pathspec-
   limited add+commit (safe: this function's own pre-existing T-1432
   contract already guarantees a commit here can never sweep in
   unrelated content). Success self-heals loudly; failure leaves the
   marker and the dirt in place for a human, never a blind reset --
   unlike land's squash residue, this dirt is small and pathspec-scoped,
   so deferring is cheap.

2. `src/frob/app/ticket_runner/__init__.py`: `reclaim_orphaned_squash_
   residue` (T-2170/T-2286, land's own squash-staging reconciliation)
   had exactly ONE caller before this change -- `land()` itself, at its
   own startup. A root left dirty by a killed land therefore stayed
   dirty until someone happened to run `land` again, not any OTHER
   mutating verb. Widened its call site into `_refuse_if_land_in_
   progress_for_dispatch`, the single pre-dispatch hook every non-
   read-only, non-land-exempt verb already runs through -- so ANY
   mutating dispatch now self-heals a killed land's residue too, before
   the ordinary DirtyMain-adjacent refusal even runs. Left the function's
   OWN safe reset-only behavior completely unchanged (out of scope,
   noted below) -- only its reachability widened.

DirtyMain itself is untouched: both reconciliations only ever act on
POSITIVE evidence (a marker), and only in the lock-free/no-live-process
case each primitive already required before this change. A genuinely
dirty root with no marker is left exactly as it was for DirtyMain to
refuse, unchanged.

Deliberately NOT changed, and why: land's own squash-residue reclaim
(`reclaim_orphaned_squash_residue`) still only ever resets, never
finishes, a killed land's staged squash. Investigated whether to make it
"finish" the same way the new ledger-commit marker does; concluded the
risk profile is materially different -- a land's squash commit legitimately
depends on prior steps (REL001 version bump, native rebuild, the T-0463
completeness assertion) that a bare re-commit of whatever happens to be
staged cannot safely re-verify without re-implementing a meaningful slice
of `_land_squash_apply` itself. A wrong "finish" there risks publishing an
incomplete land as real, which is worse than the DirtyMain block it
replaces. Filing this as a candidate follow-up rather than attempting it
under this ticket's own time/risk budget.

Positive controls, both directions, all in the new/widened test suite:
- a land killed mid-stage (existing T-0907 coverage, re-verified clean)
  and a ledger commit killed mid-add/commit both leave the shared root
  reclaimable, and a subsequent UNRELATED verb's dispatch is not
  DirtyMain-blocked by either.
- a genuinely dirty root with no marker is still refused (unchanged,
  re-verified via the full existing test_ticket_leases.py suite).
- both reconciliations name the owning ticket/marker loudly in their
  logs, never silently absorbing or discarding content.

### Changed
```
 rapid-debt.jsonl                       |   1 +
 src/frob/app/ticket_runner/__init__.py |  24 ++-
 src/frob/tickets/_leases.py            | 331 +++++++++++++++++++++++++++++++--
 tests/test_ticket_leases.py            | 193 +++++++++++++++++++
 tickets/T-2714/done-report.md          |  93 +++++++++
 5 files changed, 629 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_no_marker_is_a_silent_no_op` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_finishes_a_killed_commit_when_the_staged_content_is_still_there` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_already_advanced_tip_just_clears_the_marker` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_nothing_dirty_clears_the_marker_silently` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_finish_failure_leaves_the_marker_and_the_dirt_for_a_human` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestDispatchLandGuard::test_orphaned_squash_residue_is_reclaimed_before_a_mutating_verb_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 44 error(s), 939 warning(s), 679 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOC006@tickets/T-2705/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2714/src/frob/tickets/_leases.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
