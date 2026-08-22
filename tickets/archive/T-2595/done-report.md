## Done report

Verified the race directly before fixing it (per the ticket's own
instruction to characterise, not assume). Root cause: `run_deferred_
post_land_sweep` read `_write_baseline`'s target (an unconditional,
unlocked overwrite) after computing `fresh` from a multi-minute `frob
check`. Two sweeps computed against DIFFERENT tree states (one older,
one newer) both eventually reach that write; whichever finishes second
wins unconditionally, with no regard for which one actually reflects a
fresher view of the tree -- so a sweep computed against a stale tree can
silently discard a concurrent sweep's fresher, more-correct baseline.

Fix: `_write_baseline_cas` (src/frob/app/ticket_runner/_rapid_sweep.py)
wraps the read-decide-write in a dedicated advisory flock
(`_baseline_lock`, `.frob/rapid-sweep-baseline.lock` -- a separate lock
file from `land.lock`, so a sweep never contends with an actual land) and
only performs the write when it cannot discard newer information: no
prior baseline (write), the on-disk commit is a git ancestor of the
incoming one (write, we are at least as fresh), or ancestry is
unresolvable (write anyway -- an unmeasurable condition must not
permanently block a sweep with real findings, matching this module's
existing degrade-gracefully posture elsewhere). Only a genuinely NOT-an-
ancestor on-disk commit (a concurrent sweep's fresher write) causes a
skip, logged loudly at WARNING with the specific reason. The lock scope
is deliberately just the tiny read+write, never the multi-minute check
that produces the findings, per the ticket's own "must not turn
concurrent sweeps into a serialization bottleneck" requirement.

`run_deferred_post_land_sweep`'s call site now uses `_write_baseline_cas`
in place of the old unconditional `_write_baseline`, and the T-2571
`_baseline_write_survived` detection check is now gated on `wrote` being
`True` -- a CAS-skip already logs its own precise reason and has nothing
new to "survive".

Repro discipline: the designated repro test
(TestDeferredSweepBaselineCasRace::test_a_sweep_computed_against_a_
stale_tree_does_not_clobber_a_fresher_ones_baseline) deliberately
exercises only pre-existing public surface (`run_deferred_post_land_
sweep`, `_write_baseline`, `_read_baseline`/`_read_baseline_commit`) so
it stays COLLECTIBLE (and thus a genuine FAILED_AT_PARENT, not a
collection error masquerading as NO_VERDICT) against the tree before the
fix -- verified directly: committed the test alone first (6d9668b89),
confirmed it fails there with a real AssertionError, then committed the
fix (20f491386) and confirmed it and the rest of the suite pass.
`--check-repro` against 6d9668b89 confirms FAILED_AT_PARENT.

Ran tests/unit/test_rapid_sweep.py in full: 145/145 pass with the fix
(no FROB_WORKTREE set in the pytest environment -- with it set, several
PRE-EXISTING unrelated tests in this file fail because they spawn a real
`frob check` subprocess against a throwaway tmp_path repo and the
worktree-lease guard refuses to mutate a path outside the leased
worktree; confirmed this is not caused by this change by running the
same pre-existing tests in isolation both with and without the env var).

Found but not fixed, filed separately: none new from this ticket's own
work (T-2450's scope defect was found and filed while working the
preceding T-2593, already recorded there).

### Changed
```
 frob.lock                                  |  20 ++-
 rapid-debt.jsonl                           |   1 +
 src/frob/app/ticket_runner/_rapid_sweep.py | 232 ++++++++++++++++++++++++++++-
 tests/unit/test_rapid_sweep.py             | 201 +++++++++++++++++++++++++
 tickets/T-2593/ticket.md                   |   5 +-
 tickets/T-2595/done-report.md              |  85 +++++++++++
 tickets/T-2595/ticket.md                   |  27 +++-
 tickets/T-2614/ticket.md         |  60 ++++++++
 8 files changed, 620 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepBaselineCasRace::test_a_sweep_computed_against_a_stale_tree_does_not_clobber_a_fresher_ones_baseline` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestBaselineLock::test_no_fcntl_degrades_to_unlocked` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestBaselineLock::test_serializes_two_concurrent_holders` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestIsAncestor::test_true_when_older_is_ancestor` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestIsAncestor::test_equal_commits_are_ancestors` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestIsAncestor::test_false_when_not_an_ancestor` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestIsAncestor::test_none_on_git_failure` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestWriteBaselineCas::test_writes_when_no_prior_baseline` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestWriteBaselineCas::test_writes_when_prior_is_an_ancestor` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestWriteBaselineCas::test_skips_when_prior_is_not_an_ancestor` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestWriteBaselineCas::test_writes_when_ancestry_is_unresolvable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH102@src/frob/tickets/_doable.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2593/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2595, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
