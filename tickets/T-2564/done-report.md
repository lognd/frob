## Done report

### What was investigated

The three deliverables the ticket asked for, in order:

1. Can `land` stage-and-commit atomically, or shrink the window?
2. If a window is unavoidable, is it RECOVERABLE (a marker the next
   land can detect and reconcile)?
3. At minimum, must a land never COMMIT index content it did not
   itself stage?

### Finding: this is a clean negative -- (2) and (3) are already fixed

Reading `src/frob/tickets/_land.py`/`_land_squash.py` found that T-0907
(with T-1963's later hardening) already built exactly the mechanism
deliverable 2 asks for, landed well before this ticket was filed:

- `_write_land_repair_marker(root, ticket_id, pre_land_tip)` is called
  immediately before `_land_squash_apply` -- the ONLY step that mutates
  `root` (including staging) -- and cleared in a `finally` on any exit.
  An uncatchable `SIGKILL` between these two points leaves the marker on
  disk under `<root>/.frob/land-repair/<ticket_id>.json`.
- `_repair_stale_land_marker(root)` runs at the very START of every
  single `_land_locked` call (any ticket, any root), BEFORE that call's
  own `root_pre_land_tip` is even captured, before its own DirtyMain
  check, and before its own staging. It scans the WHOLE land-repair
  directory (not just a marker for its own ticket id) and resets `root`
  to its CURRENT `HEAD` (T-1963: never the marker's stale recorded tip,
  which would be actively destructive if a different land legitimately
  advanced `HEAD` in between), discarding whatever staged/untracked
  leftovers a crashed prior run left behind.

Because this reconciliation runs before ANY subsequent land's own
staging begins, deliverable 3's hazard -- "a land must never commit
index content it did not itself stage" -- cannot occur BY CONSTRUCTION,
not by luck: a second, unrelated ticket's land always finds `root`
already clean (or freshly cleaned) before it stages a single byte of
its own squash-apply.

This also explains the exact symptom T-2539's agent originally reported
("within about a minute a concurrent process cleared it -- git status
went from 10 staged paths to working tree clean -- with none of that
content reaching main"): that IS `_repair_stale_land_marker` doing its
job on the next `land()` call, for any ticket, not a mystery.

Deliverable 1 (true stage+commit atomicity, or narrowing the window
itself) was NOT pursued -- once 2 and 3 are closed, narrowing the
window further has no correctness payoff, only a smaller (already
harmless) blast radius. Not fixed here; not filed as a follow-up either,
since there is no known cost to the current window's width once
recovery and non-contamination are both structurally guaranteed.

### Repro / positive control added

The existing `TestSigkillMidStaging` (T-0907's own regression lock) only
covers a REAL `SIGKILL` retried by the SAME ticket. It does not by
itself prove the cross-contamination question T-2564 was filed to
answer -- that a DIFFERENT ticket's land, running shortly after, cannot
absorb the first ticket's abandoned staged content. Added
`test_unrelated_land_does_not_absorb_a_killed_lands_staged_content`,
which extends the same real-`SIGKILL`-via-`multiprocessing.fork` harness
with a SECOND, unrelated ticket landed afterward against the same root,
and asserts:

- the second land succeeds and its own diff carries only its own file;
- the killed ticket's file never reached main as a passenger;
- the killed ticket's marker is reconciled (gone) by the SECOND land,
  not by its own retry;
- the killed ticket's own retry, afterward, still lands cleanly.

Both positive controls in the class pass against the CURRENT (unmodified
in this ticket) `_land.py`/`_land_squash.py` -- this ticket's own diff
is test-only, no production code changed, consistent with a genuine
clean negative rather than a fix.

### Evidence

- `tests/test_ticket_land.py::TestSigkillMidStaging::test_unrelated_land_does_not_absorb_a_killed_lands_staged_content`
  (new, this ticket)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry`
  (pre-existing T-0907 regression lock, re-run as evidence this ticket's
  finding rests on)

No `--designate-repro` was used: there is no bug to reproduce here (the
new test is a PASSING positive control against unmodified code, not a
failing repro of a real defect) -- BUG002's confirmatory-only-evidence
concern does not apply to a ticket whose finding IS "already fixed,
confirmed by measurement."

### Gates

`uv run pytest tests/test_ticket_land.py::TestSigkillMidStaging -p no:cacheprovider -q`:
2/2 pass (must run with `FROB_WORKTREE`/`FROB_AGENT` UNSET in the
invoking shell -- these tests spawn `frob ticket new`/`land` against
throwaway `tmp_path` repos, and the T-0880-fixed leak only covers
`tests/system/**`'s own `run()` helper, not this file's direct
`new_ticket`/`land` Python calls, which inherit `os.environ` unfiltered
and trip the T-0574 worktree-lease guard against the wrong cwd if the
dispatching agent's own lease vars are still exported).

### Changed
```
 tests/test_ticket_land.py          |  88 ++++++++++++++++++++++++++++
 tickets/T-2564/done-report.md      | 117 +++++++++++++++++++++++++++++++++++++
 tickets/T-2564/ticket.md           |  21 ++++++-
 tickets/T-2680/ticket.md |  56 ++++++++++++++++++
 4 files changed, 279 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_unrelated_land_does_not_absorb_a_killed_lands_staged_content` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 37 error(s), 1094 warning(s), 697 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2564, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
