## Done report

Closed both structural holes T-1620 named, and unblocks T-1579/the
WAIVE004 auto-delete land-path re-enable (still queued, not touched here
-- this ticket's own job was closing the two holes it names, not
re-enabling the escape itself).

## 1. Zero-findings under-report

`_perf_reach_degraded_marker` (src/frob/gates/__init__.py) checked ONLY
`frob_core` staleness. Root-caused why that was incomplete: EVERY perf
rule's input, not just PERF008/012's reach analysis, passes through
`frob.lang.parse_file`'s tree-sitter grammar first
(`_perf_gate_parse_files` -> `parse_file` -> `strata_core`) -- a
content-stale-but-importable `strata_core` can silently parse fewer or
wrong symbols, under-reporting even the natively-independent PERF001-004
lexical rules the T-1578 comment claimed "stay fully trustworthy". This
is the exact 2026-08-05 incident: PERF004 read zero repo-wide against a
stale worktree while the frob_core-only marker reported healthy.

Fix: `_PERF_REACH_NATIVE_NAME` (singular) -> `_PERF_REACH_NATIVE_NAMES`
(frozenset of both declared natives, `frob_core` and `strata_core`);
`_perf_reach_degraded_marker` now trips `PERF_REACH_DEGRADED_SKIP_MARKER`
(already wired into `_degraded_verification_reason`'s "unexpected skip"
branch since T-1578 -- no change needed there) when EITHER is stale.

## 2. Sub-threshold mass staleness

`_WAIVE004_MASS_INVALIDATION_THRESHOLD = 5` is an absolute count,
structurally blind to any rule with fewer than 5 live waivers -- the
2026-08-05 incident's own 4-waiver DEPR005/DEAD001 residue slipped under
it. `_mass_invalidation_rules` (src/frob/gates/_fix_engine_sync.py) now
ALSO flags the PROPORTIONAL case: every one of a rule's live waivers
going stale in the same run, independent of the absolute count. New
`_live_waiver_counts(root)` builds a fresh `GraphSnapshot` and reuses
`frob.gates._waive._waivers_by_rule` for the denominator (best-effort:
a build failure returns `{}`, degrading to the absolute-threshold check
alone, never a crash). Threaded through
`_drop_untrustworthy_mass_stale_candidates`, which now takes `root` to
compute it.

## Acceptance criteria honored (binding, per the coordinator's brief)

Verified BOTH new checks are additive, not replacements, and do not
touch the existing diff-scoped exemption machinery
(`_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES` in `frob.gates._waive`,
read but not modified) that already tells a genuinely diff-scoped rule's
expected "0 findings on a clean backlog" apart from a degraded run for
DUP001/AFFECT001/WIRE001/SCOPE001/etc. Neither new check can fire for
those rules: the native-staleness marker is orthogonal (a `GateStats.
skipped` signal, not a per-rule finding count), and the proportional
mass-invalidation check only evaluates WAIVE004 candidates already
excluded from analysis for structurally-unverifiable rules upstream
(`_waive004_violations` skips them before ever producing a WAIVE004
finding for them to become a candidate from).

## Cuts disclosed

- docs/modules/perf.md's T-1578 section still says PERF001-004 "need no
  native at all and stay fully trustworthy" and references the now-
  renamed `_PERF_REACH_NATIVE_NAME` (singular) -- out of T-1620's
  declared scope (docs/modules/gates.md only). docs/modules/gates.md's
  own T-1578 section (in scope) is updated with the corrected
  explanation in this diff; filed T-1793 as the perf.md mirror
  follow-up, with a `frob:waive AFFECT001` at the call site naming it.
- `_WAIVE004_MASS_INVALIDATION_THRESHOLD` itself was left at 5 rather
  than lowered, per the ticket's own "either... or" framing -- the
  proportional check is the chosen fix, not a threshold change, since it
  catches the sub-threshold gap without weakening the absolute guard's
  existing behavior for rules with many live waivers.
- Widening `_worktree_natives_verifiably_healthy`
  (`src/frob/app/ticket_runner/_land_cmd.py`) was investigated and found
  to need NO change: it already calls `frob.strata.stale_natives(
  worktree)` unfiltered by native name, so it was never frob_core-only
  the way `_perf_reach_degraded_marker` was -- this is noted, not a
  silent gap.
- Re-captured post-merge (T-0754 ClaimDivergence on the first land
  attempt): a pre-existing DUP001 (tests/test_gates.py::
  TestTest013NativeUnverified.test_silent_on_executed_edge vs
  TestTest010KindValidation.test_valid_kind_not_reported, both tests
  this ticket never touched) became visible once tests/test_gates.py
  entered this ticket's scope for the strata_core marker-test fix. Not
  code this ticket introduced or should refactor under its own scope --
  captured as part of the current gate-state claim, not silently
  dropped.

### Changed
```
 docs/modules/gates.md              |  40 +++++++++--
 rapid-debt.jsonl                   |   1 +
 src/frob/gates/__init__.py         |  61 +++++++++++------
 src/frob/gates/_fix_engine_sync.py |  92 ++++++++++++++++++++-----
 tests/test_gates.py                | 137 +++++++++++++++++++++++++++----------
 tests/test_gates_ratchet.py        |  69 +++++++++++++++++++
 tickets/T-1620/done-report.md      | 101 +++++++++++++++++++++++++++
 tickets/T-1620/ticket.md           |  18 ++++-
 tickets/T-1793/ticket.md |  43 ++++++++++++
 9 files changed, 482 insertions(+), 80 deletions(-)
```

### Evidence
- `tests/test_gates_ratchet.py::TestMassInvalidationRulesProportional::test_below_threshold_but_all_live_waivers_stale_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestMassInvalidationRulesProportional::test_below_threshold_with_more_live_waivers_than_stale_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestMassInvalidationRulesProportional::test_absolute_threshold_still_fires_with_no_live_count_data` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestMassInvalidationRulesProportional::test_partial_stale_below_threshold_and_below_live_count_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPerfReachDegradedMarker::test_stale_strata_core_also_returns_the_marker` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPerfReachDegradedMarker::test_stale_unrelated_native_returns_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 1 error(s), 1393 warning(s), 721 waived
- error-findings: DUP001@tests/test_gates.py
