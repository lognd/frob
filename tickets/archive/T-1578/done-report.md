## Done report

Two layers, matching the ticket's own split.

Layer 1 -- structural signal (`src/frob/gates/__init__.py`):
`_perf_reach_degraded_marker` checks `frob.strata.stale_natives` for
`frob_core` specifically (the native `frob.graph.callgraph`'s edge-
resolution fast path uses, which PERF008/PERF012's reach analysis
walks), called from `_build_jobs` whenever `perf` is a selected gate,
AFTER `run_gates`'s own `_maybe_autorebuild_natives` already had its
chance to fix a stale `frob_core` in place. This only fires when that
auto-rebuild was disabled or genuinely failed -- a content-stale
`frob_core` is invisible to NATIVE001, which only ever checks import
FAILURE (`unimportable_natives`), never staleness. When it fires, the
new `PERF_REACH_DEGRADED_SKIP_MARKER` ("perf_reach_native_stale") is
appended to `GateStats.skipped` -- perf_gate itself still runs
unchanged (PERF001-004 need no native and stay fully trustworthy), but
`frob.gates._fix_engine._degraded_verification_reason`'s existing
"unexpected skip" branch (T-1323) now catches this specific
degradation too, instead of only ever seeing "0 findings" from
PERF008/PERF012 with nothing to explain why.

Layer 2 -- land preflight (`src/frob/app/ticket_runner/_land_cmd.py`):
`_worktree_natives_verifiably_healthy` runs the SAME auto-rebuild
attempt `run_gates` itself would, then checks EVERY declared native
(not just frob_core -- the WAIVE004 self-run is a FULL gates pass) for
staleness/importability directly. `_tier_a_pre_land_step` calls this
BEFORE `apply_tier_a_fixes` and excludes `WAIVE004` from that land's
Tier-A batch when it says no, logged at INFO rather than the scary
ERROR `fix_waive004_stale_waiver`'s own guards would have logged after
paying for the full run anyway. Same eventual outcome (nothing
deleted), cheaper, quieter.

`docs/modules/perf.md` gained a new "Perf-reach native staleness
signal (T-1578)" section (the `frob:doc` anchor Layer 1's public
`PERF_REACH_DEGRADED_SKIP_MARKER` constant points at) and
`docs/modules/gates.md` gained a matching "Perf-reach content-
staleness signal + land preflight (T-1578)" subsection right after the
existing NATIVE001 auto-rebuild writeup, cross-linking both.

Found and fixed two verification-time regressions while checking this
ticket's own `frob check --only gates-native` (unscoped, repo-wide,
per playbook section 6c -- these were not diff-scoped to T-1578's own
touched set, they were real debt my earlier T-1577/T-1579 commits in
this same worktree introduced):

- ARCH001: T-1579's per-rule mass-invalidation filtering pushed
  `_waive004_verified_candidates` past the 60-line ceiling -- extracted
  `_drop_untrustworthy_mass_stale_candidates`, no behavior change.
  Committed as its own T-1579-attributed commit (43e2a9b7), not folded
  into this ticket's own diff.
- DUP001: T-1577's two WIRE001/SCOPE001 exemption tests were 95%
  identical bodies -- parametrized into one
  `test_waive004_exempts_diff_scoped_rules` test over both rules, with
  T-1577's own evidence rebound via `frob ticket evidence --replace`.
  Committed as its own T-1577-attributed commit (46814e9c).

Merged `main` mid-ticket (playbook section 1's warm-up merge, run again
here since main had moved considerably since this worktree's original
merge and the deletion-filter check flagged two files main had
recently added that this branch predated) -- confirmed clean (`git
diff main --diff-filter=D --stat` empty after merging, no conflict
markers, all touched-test suites re-verified green post-merge).

`frob check --land-parity` reports CLEAN (0 unscoped errors) against
the current, post-merge worktree tree.

### Changed
```
 docs/modules/gates.md                     | 116 ++++++++++--
 docs/modules/gates_e501_autofix.md        |  31 +++-
 docs/modules/perf.md                      |  39 ++++
 src/frob/app/ticket_runner/_land_cmd.py   |  42 ++++-
 src/frob/gates/__init__.py                |  59 ++++++
 src/frob/gates/_fix_engine.py             | 194 ++++++++++++++------
 src/frob/gates/_fmt_directives.py         |  10 +-
 src/frob/gates/_waive.py                  |  37 +++-
 tests/test_gates.py                       | 139 +++++++++++++++
 tests/test_gates_fix_engine.py            |  78 ++++++++
 tests/test_ticket_work_and_land_finish.py |  61 +++++++
 tickets.md                                | 286 +++++++++++++++++++++++++++++-
 12 files changed, 1007 insertions(+), 85 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestPerfReachDegradedMarker::test_no_stale_natives_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPerfReachDegradedMarker::test_stale_frob_core_returns_the_marker` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPerfReachDegradedMarker::test_stale_unrelated_native_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestWorktreeNativesVerifiablyHealthy::test_healthy_natives_return_true` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestWorktreeNativesVerifiablyHealthy::test_stale_after_autorebuild_attempt_returns_false` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestWorktreeNativesVerifiablyHealthy::test_unimportable_native_returns_false` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 6236 warning(s), 798 waived
- error-findings: none (measured, zero errors)
