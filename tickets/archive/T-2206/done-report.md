## Done report

frob:no-behavior-change reason="reworded an English comment (test-only, no code path) so it no longer lexically matches TEST010's frob:tests directive scanner; no behavior changed"

Re-measured the sweep's 17 claimed (rule, file) identities against the
current tree rather than trusting the sweep's stale count.

Genuine at time of measurement, fixed here:
- TEST010 tests/test_ticket_work_and_land_finish.py:832 -- a prose comment
  read "... with no frob:doc/frob:tests edge." which TEST010's lexical
  directive scanner misparsed as an attempted `frob:tests` directive with
  verb "doc/frob:tests". Reworded to "doc/test edge (the `frob:doc` /
  `frob:tests` directive pair)" so it no longer trips the scanner. Confirmed
  fixed: `uv run frob check --only test` no longer emits TEST010 for this
  file, and the "malformed directive" warning is gone.

Already resolved as a side effect of T-2260 landing first (shared files,
same repo): DRIFT001 src/frob/lang/_nodes.py, E501 src/frob/lang/_nodes.py.

Genuine but NOT fixed here -- filed as T-2303 instead of forced blind:
- ARCH001 src/frob/app/telemetry.py, src/frob/app/ticket_runner/_land_cmd.py
  (x3 functions), src/frob/app/ticket_runner/_new.py -- real function-length
  violations (62-151 lines against a 60-line threshold)
- ARCH103 src/frob/app/ticket_runner/_land_cmd.py -- real I/O+decision-point
  complexity findings
- PERF004/PERF008 src/frob/app/ticket_runner/_land_cmd.py,
  src/frob/app/ticket_runner/_rapid_sweep.py -- real loop-invariant/sort-in-
  loop findings
- SELFAUDIT001 design -- 2 undeclared capability effects + a ratchet ceiling
  overrun (22 sites vs 21 committed)
All of the above are UNATTRIBUTED by the sweep's own symbolic-reachability
attribution (many or zero candidate commits), consistent with long-
accumulated debt in `_land_cmd.py`'s land machinery rather than something
T-2199 (the land this sweep fired from) introduced. Splitting 120-151 line
land-critical functions safely is its own scoped refactor, not something to
force inside a sweep-regression ticket's remaining budget -- filed as T-2303
(kind=bug, scope src/frob/app/telemetry.py, _land_cmd.py, _new.py,
_rapid_sweep.py, design) with every finding's exact message quoted.

Confirmed STALE (did not reproduce on the current tree, no fix needed):
- COV004 (3 tickets/ attachment .md files) -- rule/finding entirely absent
  from a fresh `frob check --only coverage`
- DOC011 docs/design/gate-semantics-classification.md,
  docs/guides/coordinator-scripts.md -- absent from `frob check --only doclink`
  (only DOC001 was present, a different rule/file)
- DRIFT001 src/frob/app/ticket_runner/_land_cmd.py -- absent from
  `frob check --only drift`
- TEST010 tests/test_lang.py -- absent from `frob check --only test`

TICK004 tickets.md was genuine (repeated ticket-rot warnings) but is ambient,
continuously-reproducing ticket-queue-age state, not something a code change
in this ticket's scope affects; not filed separately since it already has
its own standing gate (TICK004) surfacing it every run.

Changed: tests/test_ticket_work_and_land_finish.py (comment reword only)

Evidence: tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol
(passes; note this test spawns its own worktree, so it must be run with
FROB_AGENT/FROB_WORKTREE unset in the invoking shell or it spuriously fails
on the section-5b-style leak -- this file is not under tests/system/**, so
the T-0880 fix does not cover it; worth a follow-up but out of this
ticket's declared scope)

Filed: T-2303 (ARCH001/ARCH103/PERF004/SELFAUDIT001 structural debt)

Gates: scope/prework clean at start; targeted pytest run above green;
`frob check --only test` confirms TEST010 clear for this file.

Claimed vs genuinely-new: 17 claimed identities, 10 genuinely reproduced
(1 fixed here, 6 filed as T-2303, TICK004 left to its own standing gate,
2 already fixed by T-2260's land), 7 stale.

### Changed
```
 tests/test_ticket_work_and_land_finish.py | 3 ++-
 tickets/T-2206/ticket.md                  | 4 +++-
 2 files changed, 5 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 0 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2206/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2206/scripts/fleet_status.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2206/tests/test_ticket_land.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md
