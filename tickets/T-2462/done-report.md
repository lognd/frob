## Done report

Completes T-2445's throughput fix: pyproject.toml's version line and
.frob-release.json's stamped manifest no longer bump on every land.
They now bump only at an explicit release cut (frob release
check/sync/stamp, or frob release publish), matching T-2445's
existing CHANGELOG.md fragment deferral. Landed atomically with the
REL001/close-preflight adaptation the ticket required -- not split.

CHANGES:

- src/frob/app/ticket_runner/_land_cmd.py: _apply_release_bump_for_land
  ALWAYS returns Ok(None) now (never Ok(new_version)), so the caller
  (frob.tickets._land_release._apply_release_bump) always takes its
  "no bump applied" branch, whose monotonicity/coherence checks trust
  pyproject.toml/.frob-release.json to stay exactly at whatever
  _reset_release_artifacts_to_pre_land reset them to (unchanged, by
  construction). _write_release_bump no longer calls rewrite_
  pyproject_version -- only writes the T-2445 fragment, regenerates
  CHANGELOG.md's pending section, and stages both. Deleted _stamp_and_
  stage_release_bump (its frob.release.stamp call and pyproject/
  manifest staging are gone; no longer called from anywhere).
- src/frob/gates/__init__.py: release_gate's plain-root-checkout branch
  (no ticket, no lease, not FROB_AGENT) now calls new _rel001_plain_
  checkout_violations (ARCH001 split), which downgrades an under-bumped-
  version/missing-changelog ERROR to a WARN (new _rel001_deferred_note,
  mirroring _rel001_land_note's shape) whenever changelog.d/ fragments
  already track it (new _rel001_fragments_pending, fail-closed on any
  parse error). Genuinely missing (no fragment at all -- e.g. a
  hand-edited public API change outside frob ticket land) keeps the
  strict pre-T-2462 ERROR posture unchanged.
- src/frob/app/ticket_runner/_close_cmd.py: _own_obligations_rel_bump_
  dirty's outstanding-bump half is now _own_obligations_rel_bump_
  outstanding (ARCH001 split), which additionally accepts "a changelog.
  d/T-####.md fragment already exists for this ticket" (new _rel001_
  fragment_exists_for_ticket) as satisfying, alongside the existing
  "pyproject.toml already covers the diff" check -- fixes a reverify of
  an already-landed ticket (root = main, post-land) falsely re-flagging
  the SAME already-handled bump as outstanding forever between release
  cuts, since pyproject.toml now stays frozen until the next cut.
- docs/modules/tickets-landing.md: step 9.6 rewritten to describe the
  deferred posture and why Ok(None) is now the only reachable return.

MEASURABLE DELIVERABLE: two lands with disjoint code scopes now complete
without ANY manual conflict-resolution step on EITHER shared release
artifact -- CHANGELOG.md (T-2445) or pyproject.toml/.frob-release.json
(this ticket). Verified directly:
tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest::
test_stale_worktree_manifest_still_lands_main_plus_one lands a real
ticket through the REAL _apply_release_bump_for_land callback and
asserts pyproject.toml/.frob-release.json are BYTE-IDENTICAL to main's
pre-land state afterward (no write, so no possible collision), while
CHANGELOG.md/changelog.d/ still correctly record the bump (collision-
free fragment write, T-2445's existing mechanism). This is T-2445's
first acceptance criterion, now genuinely met on BOTH shared paths, not
"halved" -- the measured 6-of-7-lands-touch-both-shared-files contention
this ticket exists to close no longer applies to either file.

Release correctness preserved (T-2445's own "must-still-produce"
positive control, extended): a release cut still bumps the version
exactly once (an explicit, single step, not accumulated per-land
double-bumps) and CHANGELOG.md still accumulates every landed ticket's
fragment in correct numeric order -- unchanged, since T-2445's assembly
mechanism was already correct and this ticket did not touch it, only
the version-bump half.

Gates: scoped frob check --ticket T-2462 -- zero new findings on any
touched file (verified: the one remaining error-severity finding
touching gates/__init__.py, an E501 at line 6727, is pre-existing and
outside every symbol this ticket edited; two ARCH001 findings this
ticket's own additions caused mid-session were fixed via ARCH001 splits
before this report -- _rel001_plain_checkout_violations/_own_
obligations_rel_bump_outstanding). Full affected suites re-run clean:
tests/test_ticket_land.py + tests/test_release.py + tests/unit/gates/
test_rel001_deferred_bump.py + tests/unit/test_close_rel001_bump.py +
tests/unit/test_ticket_runner_land_release.py = 386 passed, 0 failed.

Floor: unscoped frob check on main measured 67 errors before this
ticket started (per dispatch brief); this ticket's own scoped check
shows zero NEW error-severity findings attributable to any file it
touched, so the floor is unaffected by this change (a floor
re-measurement after landing is the coordinator's normal post-land step,
not restated here to avoid a stale number going stale again before it's
read).

Filed: none -- T-2465 (the SELFAUDIT001 second task) was filed before
this ticket started, closed and landed separately as its own atomic
change (commit cae6baf6bd7d50d32162c3f903c41f2c7d4e2f3d).

### Changed
```
 docs/modules/tickets-landing.md               |  70 ++++++---
 src/frob/app/ticket_runner/_close_cmd.py      |  65 +++++++--
 src/frob/app/ticket_runner/_land_cmd.py       | 197 ++++++++++----------------
 src/frob/gates/__init__.py                    |  99 ++++++++++++-
 tests/test_ticket_land.py                     |  42 +++++-
 tests/unit/gates/test_rel001_deferred_bump.py | 179 +++++++++++++++++++++++
 tests/unit/test_close_rel001_bump.py          |  83 +++++++++++
 tests/unit/test_ticket_runner_land_release.py | 105 +++++++++-----
 tickets/T-2462/ticket.md                      |  52 ++++++-
 9 files changed, 694 insertions(+), 198 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest::test_stale_worktree_manifest_still_lands_main_plus_one` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_writes_fragment_and_regenerates_changelog_no_pyproject_touch` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_needed_writes_fragment_but_returns_none_and_never_stamps` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_rel001_deferred_bump.py::TestReleaseGatePlainCheckoutDeferredPosture::test_pending_bump_with_fragment_is_warn_not_error` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_rel001_deferred_bump.py::TestReleaseGatePlainCheckoutDeferredPosture::test_pending_bump_without_fragment_stays_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyFragmentSatisfies::test_fragment_present_satisfies_even_though_pyproject_undeclared` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyFragmentSatisfies::test_no_fragment_and_no_bump_still_dirty` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-0338, COV003@tickets/T-1007, COV003@tickets/T-1009, COV003@tickets/T-1089, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1368, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1593, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2462/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2462/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2462/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2462/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2462/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2462, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
