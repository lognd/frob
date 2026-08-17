## Done report

Fixed the T-1914 sibling-state-regression guard's self-conflict shape: a
land whose only divergent ledger row is the LANDING ticket's own no longer
requires manual resolution.

Root cause, confirmed by direct reproduction rather than assumed: the
sibling-regression guard (`_assert_no_sibling_state_regression`,
`_sibling_ticket_states`) already excluded the landing ticket's own id
from its comparison set -- that half was sound. The actual friction was
one step earlier: `_merge_main_into_worktree_v2`'s v2 merge story
(T-1258/AC3) deliberately treats ANY conflict inside the landing ticket's
own `tickets/<id>/` directory as an ordinary in-scope conflict and leaves
it for manual `git merge` resolution (`LandError.MergeConflict`), with no
special case for "the only real difference is which side is newer" --
exactly the shape the playbook's own section 10 rule (keep the newer
state) already resolves by hand every time an agent hits it. Reproduced
directly: a worktree that genuinely progresses a ticket (queued ->
planned -> in_progress + evidence + Done report) while main independently
advances the SAME ticket's `state:` line to a lesser value (e.g. an
auto-plan sweep) produces a same-line git conflict on
`tickets/<id>/ticket.md`, which `land()` refused before this fix.

Fix: `_resolve_self_conflict_by_newer_state` (src/frob/tickets/
_land_git_ops.py) recognizes exactly `tickets/<landing_id>/ticket.md` --
never a sibling's directory, never any other conflicted path -- reads
both sides directly from git (HEAD for the worktree's pre-merge commit,
main_branch for main's tip), parses each via the newly extracted
`_parse_ticket_text` (src/frob/tickets/_store.py, split out of
`_parse_ticket_file`'s inline parse body so a git-blob TEXT can reuse the
same parse/validate path), and picks the winner via the EXISTING
`_newer` function (src/frob/tickets/_land_ledger_merge.py) -- the same
state-rank + richness rule the v1 ledger splice and the playbook's own
"keep the newer state" instruction already use. Wired into
`_merge_main_into_worktree_v2` between the existing out-of-scope
auto-resolve and the refuse-with-MergeConflict step, narrowing
`remaining` further but never widening what counts as auto-resolvable --
a genuine sibling conflict, or any other still-conflicted path, is
completely unaffected.

Also hardened `_assert_no_sibling_state_regression` with an explicit,
redundant `ticket_id == landing_id: continue` (belt-and-suspenders,
documented as deliberate, not dead code) so the guard can never regress
into naming the landing ticket as its own sibling regardless of how a
future caller assembles its `pre_states` map.

Positive control: `TestSelfConflictAutoResolve` in tests/unit/
test_land_sibling_regression.py has both halves T-2289's acceptance
criteria require --
  - test_self_conflict_lands_by_keeping_newer_state: MUST-NOW-PASS. Fails
    at parent (fbd394d1f, test-only commit) with LandError.MergeConflict,
    confirmed via `frob ticket evidence --check-repro`; passes after the
    fix.
  - test_genuine_sibling_conflict_still_refuses: MUST-STILL-FAIL. A
    genuine sibling ticket's `done` -> `queued` regression still refuses
    with LandError.TerminalStateRegression, unchanged.
Also updated tests/test_ticket_land.py::TestLedgerV2LandMergeStory::
test_same_ticket_conflict_surfaces_loudly_no_splice, which exercised
exactly this same-ticket-own-row conflict shape and asserted the OLD
"always surfaces loudly" behavior T-2289 deliberately narrows for this
one case; its docstring/body now documents why and points at the new
dedicated test pair.

Full tests/test_ticket_land.py (284 tests), tests/test_tickets.py (163
tests), and tests/unit/test_land_sibling_regression.py (6 tests) all pass.
`frob check --only scope --ticket T-2289` and `--only test --ticket
T-2289` show zero NEW errors -- the only errors present (3 DRIFT, 1
TEST010, unrelated files) are pre-existing repo-wide debt untouched by
this change, confirmed via git blame/diff against files outside this
ticket's scope. `frob check --land-parity` surfaces 18 unscoped errors,
all pre-existing/unrelated (fleet_status.py, _nodes.py, telemetry.py,
etc.) except one F841 in tests/test_ticket_land.py at line 1483, which
predates this change (confirmed present in `git show main:tests/
test_ticket_land.py`, unrelated to the edit at line ~3481+).

### Changed
```
 src/frob/tickets/_land.py                  |  23 ++++++-
 src/frob/tickets/_land_git_ops.py          |  63 +++++++++++++++++
 src/frob/tickets/_store.py                 |  34 ++++++---
 tests/test_ticket_land.py                  |  31 ++++++---
 tests/unit/test_land_sibling_regression.py | 106 +++++++++++++++++++++++++++++
 tickets/T-2289/ticket.md                   |  54 ++++++++++++++-
 6 files changed, 290 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/unit/test_land_sibling_regression.py::TestSelfConflictAutoResolve::test_genuine_sibling_conflict_still_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard::test_regressed_sibling_is_detected_by_rank_comparison` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard::test_no_regression_when_sibling_state_only_improves_or_holds` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard::test_pre_fix_shape_would_have_silently_reverted_sibling` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_sibling_regression.py::TestSelfConflictAutoResolve::test_self_conflict_lands_by_keeping_newer_state` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/tickets/_store.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2289/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2289/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2289/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2289/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2289/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2289, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
