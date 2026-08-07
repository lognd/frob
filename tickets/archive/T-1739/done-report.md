## Done report

frob:waive BUG002 reason="T-1715 landed first in this shared two-ticket worktree and, with --allow-cross-ticket, necessarily carried this ticket's passenger code (the sweep_worktrees liveness gate) onto main in the SAME commit -- both tickets' code physically arrived on main together by construction, since they share one mechanism per the ticket text's explicit instruction not to write a second scanner. T-1739's own designated repro test therefore already PASSES at main (parent) by the time this land runs, not because the defect was never real (the 2026-08-07 dry-run in the ticket body reproduces it directly against the pre-fix binary) but because there is no post-T-1715, pre-T-1739 commit on this branch where the fix is absent -- the repro-at-parent/pass-at-fix shape BUG002 wants does not exist for a ticket whose own fix was already delivered by a sibling's land. See docs/modules/tickets.md#worktree-liveness-scan-t-1715-t-1739 for the joint-landing rationale."

Fix: `frob worktree sweep`'s keep-criteria (lease/dirty/age) had no
liveness check at all -- a 2026-08-07 dry-run during a four-agent drive
caught them exactly inverted (the one worktree kept belonged to a
RETIRED agent's stale lease; the three marked for removal belonged to
LIVE agents, one mid-implementation on a critical ticket). `dirty`
under-covers precisely because a well-behaved agent commits its own
work-in-progress as this repo's own stall-insurance guidance instructs --
following the guidance made a worktree look MORE removable, not less.

`_sweep_verdict_for_worktree` now runs a liveness check FIRST, before
dirty/lease/age, using the exact same `scan_for_live_worktree_process`
primitive T-1715 introduced (reused, not a second scanner, per the
ticket's explicit instruction) -- a candidate with a live process cwd'd
into it is unconditionally `kept:live`, naming the pid, regardless of
whether it is clean/unleased/recent. `frob worktree sweep --force`
overrides this specific gate (dirty/age are unaffected). `--dry-run`'s
preview reflects the same verdict as a real sweep.

`_sweep_verdict_for_worktree` and `sweep_worktrees` were also split
(`_kept_live_verdict_if_process_present`, `_kept_lease_or_age_verdict`)
to stay under this repo's own ARCH001 line budget after the new gate was
added; `_live_lease_for_worktree` was factored out of the pre-existing
inline lease loop so T-1715's `--finish` refusal and this sweep gate
make the identical lease-liveness judgment rather than two copies.

T-1739's own body also raised a lease/state disagreement (a stale lease
naming the wrong ticket as `doable --show-blocked`'s holder while the
ledger has a different ticket queued). That is investigated and
addressed as its own ticket, T-1743 (attribution + a supported release
path for an orphaned lease) -- read there before assuming it duplicates
this ticket; it does not, this ticket's scope is the liveness scan only.

docs/modules/tickets.md's new "Worktree liveness scan (T-1715, T-1739)"
section (added under T-1715, shared with this ticket) documents both
incidents and the shared mechanism; docs/modules/app.md's runner summary
picked up the CLI surface change (`--force`, `kept:live`).

### Changed
```
 design/frob.strata                         |  55 +++---
 docs/modules/app.md                        |   7 +-
 docs/modules/tickets.md                    |  92 +++++++++
 frob.lock                                  |   4 +-
 rapid-debt.jsonl                           |   1 +
 src/frob/_cli_parsers/_ticket/_progress.py |  15 ++
 src/frob/app/ticket_runner/_land_cmd.py    |  81 ++++++--
 src/frob/app/worktree_runner.py            |  52 +++--
 src/frob/tickets/_leases.py                | 298 +++++++++++++++++++++++++----
 tests/test_worktree_guard.py               |  86 +++++++++
 tests/unit/test_land_finish_guard.py       | 271 ++++++++++++++++++++++++++
 tickets.md                                 | 165 +++++++++++++++-
 12 files changed, 1029 insertions(+), 98 deletions(-)
```

### Evidence
- `tests/test_worktree_guard.py::TestSweepWorktreesLiveProcess::test_clean_no_lease_recent_head_live_process_kept` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestSweepWorktreesLiveProcess::test_force_overrides_the_live_process_keep` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_finds_a_process_cwd_into_the_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_none_when_no_process_matches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 2 error(s), 598 warning(s), 730 waived
- error-findings: PRE001@tickets/T-1739, TICK003@tickets.md
