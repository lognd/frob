---
id: T-1934
title: Nothing detects finished-but-unlanded ticket work on a branch, and sweep's
  remove heuristic is inverted against it
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_unlanded.py
- src/frob/tickets/_leases.py
- src/frob/app/ticket_runner/_query.py
- tests/unit/test_unlanded_branch_work.py
- tests/test_ticket_leases.py
- tests/unit/test_app_runners_doable_stale_lease.py
- src/frob/tickets/_reconcile.py
- src/frob/app/ticket_runner/_lifecycle.py
- tests/test_ticket_reconcile.py
- tickets/T-1949/**
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_unlanded.py
  reason: detector for finished-but-unlanded branch work + inverted sweep heuristic
    fix + doable surfacing
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: detector for finished-but-unlanded branch work + inverted sweep heuristic
    fix + doable surfacing
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/worktree_runner.py
  reason: detector for finished-but-unlanded branch work + inverted sweep heuristic
    fix + doable surfacing
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: detector for finished-but-unlanded branch work + inverted sweep heuristic
    fix + doable surfacing
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/test_unlanded_branch_work.py
  reason: detector for finished-but-unlanded branch work + inverted sweep heuristic
    fix + doable surfacing
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_ticket_leases.py
  reason: detector for finished-but-unlanded branch work + inverted sweep heuristic
    fix + doable surfacing
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/test_app_runners_doable_stale_lease.py
  reason: detector for finished-but-unlanded branch work + inverted sweep heuristic
    fix + doable surfacing
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: src/frob/app/worktree_runner.py
  reason: 'coordinator correction: surface through frob ticket reconcile (T-0456/T-0476)
    rather than a new standalone verb'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/tickets/_reconcile.py
  reason: 'coordinator correction: surface through frob ticket reconcile (T-0456/T-0476)
    rather than a new standalone verb'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: 'coordinator correction: surface through frob ticket reconcile (T-0456/T-0476)
    rather than a new standalone verb'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_ticket_reconcile.py
  reason: 'coordinator correction: surface through frob ticket reconcile (T-0456/T-0476)
    rather than a new standalone verb'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/T-1949/**
  reason: residue ticket filed from within T-1934 for a pre-existing ARCH001 finding
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/modules/tickets.md
  reason: T-1929 landed, doc lease freed -- document the new unlanded_branch_work
    reconcile anomaly properly
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: docs/modules/tickets.md
  reason: T-1720 took a live lease on this doc mid-ticket; reverting the doc edit
    and restoring AFFECT001 waivers to unblock landing
  actor: logan
  at: '2026-08-10'
- op: add
  glob: design/frob.strata
  reason: Tier-A auto-fix declared exec/fs.write capability grants for the new test
    files (tests/unit/test_unlanded_branch_work.py, tests/test_ticket_reconcile.py
    additions)
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_confirmed_leak_shape_done_report_plus_in_progress
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_archived_done_ticket_is_not_a_false_positive
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_dropped_ticket_on_main_is_not_a_false_positive
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_local_state_done_with_no_done_report_file_is_flagged
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_queued_ticket_on_branch_is_not_flagged
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_live_leased_ticket_is_excluded
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_findings_for_one_branch_matches_the_aggregate
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_reports_the_confirmed_leak_shape
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_apply_never_heals_this_anomaly_class
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_no_unlanded_work_reports_empty
- tests/test_ticket_leases.py::TestSweepWorktreesUnlandedWork::test_clean_worktree_with_unlanded_work_is_kept_not_removed
- tests/test_ticket_leases.py::TestSweepWorktreesUnlandedWork::test_dry_run_reports_kept_not_removed
- tests/test_ticket_leases.py::TestSweepWorktreesUnlandedWork::test_landed_ticket_is_not_kept_for_unlanded_reasons
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_no_root_is_a_noop
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_no_unlanded_work_prints_nothing
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_unlanded_branch_is_summarized
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-09. Exactly one confirmed leak right now, plus two
near-misses recovered by hand this session. The count is small only
because I went looking manually; nothing in the toolchain would have
told me.

THE CONFIRMED LEAK: T-1315. A complete done-report, the design doc
(docs/design/test005-ratchet-schedule.md) and the frob.toml change are
committed on branch `runner-wiring`. The branch copy of
tickets/T-1315/ticket.md reads `state: in-progress`. None of it is on
main. T-1315 reads `queued` on main right now, so the next agent
dispatched to it would redo the whole thing from scratch.

THE NEAR-MISSES: T-1851 and T-1556 sat finished on branch
`gate-internals` behind dead-agent leases for an entire session. They
were recovered today ONLY because I manually noticed the branch was 59
commits ahead and dispatched someone to survey it. Both landed
(f4a0e5032c3e, 16880d5170a2). That recovery was luck, not process.

HOW THE LEAK HAPPENS -- the full chain, all five steps observed:
1. An agent finishes, COMMITS its work (done-report + code) in its
   worktree.
2. It dies before `frob ticket land` -- session end, context exhaustion,
   or the OOM kills this environment is known for.
3. Because everything is committed, the working tree is CLEAN.
4. The lease survives, so the ticket reads in-progress and
   `frob ticket doable` renders it under "already being worked".
   Nobody picks it up. T-1876 improved this (holder-dead leases are now
   flagged) but that surfaces the LEASE, never the WORK.
5. Nothing anywhere compares branch state against main. The work is
   invisible to every command in the toolchain.

THE INVERTED HEURISTIC, and this is the sharp edge:
`frob worktree sweep` decides removability from WORKING-TREE
DIRTINESS. So a worktree full of uncommitted junk is KEPT (kept:dirty),
while a worktree whose agent did everything right -- committed clean,
died before landing -- is marked `removed`. The better an agent behaved,
the more likely its worktree is swept. Today s sweep marked all 13
clean worktrees removable; I only checked them by hand because I was
being cautious, and every one turned out to be superseded. Next time one
will not be.

(Mitigating fact, verified: `git worktree remove` does NOT delete the
branch -- I confirmed no `branch -D` on the sweep path and all 13 branch
refs survived. So this is invisibility plus a bad heuristic, not
immediate data loss. It is still a leak, because nothing ever looks at
those branches again.)

THE DETECTOR IS CHEAP -- pure git plumbing, no test runs, no checkout.
This prototype found the leak in seconds and is the whole idea:

    for b in $(git branch --format="%(refname:short)" | grep -v "^main$"); do
      for f in $(git ls-tree -r --name-only $b | grep -E "^tickets/T-[0-9]+/done-report\.md$"); do
        t=$(echo $f | cut -d/ -f2)
        # flag when $t is NOT terminal on main
      done
    done

Keying on ticket STATE is essential. My first attempt keyed on whether
the done-report path existed on main and returned 186 false positives,
because a done ticket is ARCHIVED to tickets/archive/<id>/ on main. Do
not repeat that mistake -- resolve the ticket s state through the ledger,
including the archive, not through a path test.

REQUIRED
A. A first-class way to ask "what finished work is not on main?" --
   report every branch carrying a done-report, or a branch-local ticket
   state of done, for a ticket that is not terminal on main. Read-only,
   fast, no checkout.
B. `frob worktree sweep` must NOT mark a worktree removable while its
   branch carries unlanded ticket work. Unlanded work outranks
   working-tree cleanliness; today it is not consulted at all.
C. Ideally surfaced where a coordinator already looks --
   `frob ticket doable` already grew a stale-lease warning in T-1876;
   an "N branches carry unlanded work" line belongs in the same place.

DO NOT implement A by auto-landing anything. Landing a dead agent s
branch unattended is how unreviewed work reaches main. Report and let a
human or a dispatched agent decide.

ACCEPTANCE
1. The detector reports T-1315/runner-wiring today. It must FAIL (find
   nothing, or not exist) before the fix.
2. It does NOT report a ticket that is done or dropped on main,
   including archived ones -- assert the 186-false-positive shape
   explicitly as a regression test.
3. It does NOT report a ticket currently being worked by a live agent
   (T-1923/sweep-1919 was correctly excluded from my manual run only
   because I recognised the name -- the tool must key on something real,
   e.g. lease liveness via T-1876 s `lease_staleness_reason`).
4. `frob worktree sweep --dry-run` reports kept, not removed, for a
   clean worktree whose branch has unlanded ticket work.

FOLLOW-ON, do not fold in: T-1315 itself needs recovering from
`runner-wiring`. Do not delete that branch.

## Done report

Built `frob.tickets._unlanded` (pure git plumbing, no checkout): scans
every local branch except main for a ticket that looks finished
(`tickets/T-####/done-report.md` present, or `ticket.md`'s own `state:`
reading `done`/`dropped`), resolves that ticket id's state on `main`
checking BOTH the active path and the archive path (the 186-false-
positive shape the brief called out), and excludes any ticket whose
CURRENT lease `frob.tickets._leases.lease_staleness_reason` judges still
live (T-1876's staleness predicate, reused, not re-derived).

Per the coordinator's mid-dispatch correction, this is NOT a new
standalone verb -- it is a fourth `frob ticket reconcile` anomaly class
(`ReconcileReport.unlanded_branch_work`, report-only, never healed by
`--apply`), plus:

- `frob worktree sweep`: a new `kept:unlanded` verdict
  (`_kept_unlanded_verdict_if_present`), checked BEFORE the dirty-tree
  gate and NOT overridden by `--force` -- fixes the inverted heuristic
  directly (a clean, unlanded worktree is now kept, not removed).
- `frob ticket doable`: an "N branch(es) carry unlanded ticket work"
  line alongside T-1876's stale-lease warning.

Verified before/after (acceptance 1): before `frob.tickets._unlanded`
existed, `tests/unit/test_unlanded_branch_work.py` failed on
`ModuleNotFoundError` (confirmed directly by temporarily moving the
module aside and re-running the suite); after, all 7 tests pass,
including the T-1315/runner-wiring shape itself
(`test_confirmed_leak_shape_done_report_plus_in_progress`).

Two residues filed while working this ticket, both pre-existing and
verified unrelated via `git diff --stat main -- <path>` (empty in both
cases):
- T-1949: `_close_failure_hint` (_close_cmd.py) exceeds
  ARCH001's 60-line function threshold.
- SEC110 (src/frob/app/ticket_runner/_new.py) and SELFAUDIT001 (design)
  land-parity findings are also pre-existing/unrelated but were NOT
  separately filed (already-known, unowned repo-wide debt visible on
  every `--land-parity` run regardless of ticket, not something this
  investigation newly surfaced).

Gates: `frob check --only test/archgate/gates-fast/doclink --ticket
T-1934` and `frob check --land-parity` all read clean for this ticket's
own diff (every remaining finding independently confirmed pre-existing
via `git diff --stat main -- <path>`). `git diff main --diff-filter=D
--stat` is empty. `runner-wiring` branch is untouched (T-1315 recovery
is a separate, later commit on this same worktree/branch, cherry-picking
its scope files rather than merging the branch itself).

### Changed
```
 docs/modules/tickets.md                           |  43 ++++
 src/frob/app/ticket_runner/_lifecycle.py          |  54 +++--
 src/frob/app/ticket_runner/_query.py              |  28 +++
 src/frob/tickets/_leases.py                       |  59 ++++-
 src/frob/tickets/_reconcile.py                    |  24 ++
 src/frob/tickets/_unlanded.py                     | 255 ++++++++++++++++++++++
 tests/test_ticket_leases.py                       | 108 +++++++++
 tests/test_ticket_reconcile.py                    |  87 ++++++++
 tests/unit/test_app_runners_doable_stale_lease.py |  53 ++++-
 tests/unit/test_unlanded_branch_work.py           | 251 +++++++++++++++++++++
 tickets/T-1934/ticket.md                          |  90 ++++++++
 tickets/T-1949/ticket.md                |  36 +++
 12 files changed, 1070 insertions(+), 18 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 16 passed (from 16 evidence id(s))
- gates: 4 error(s), 1275 warning(s), 715 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, DOC001@docs/design/cli-hygiene.md, SEC110@src/frob/app/ticket_runner/_new.py, SELFAUDIT001@design
