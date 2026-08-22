## Done report

Root cause confirmed by reading src/frob/gates/_waive.py::_match_waiver's
symref-less (file-scoped/package-prefix) branch: when `violation.symref`
is None, the function returned the FIRST candidate in `waivers_by_rule`'s
build-order list that matched by file -- so for a file with 2+
`frob:waive PERF008 reason="..."` comments at different lines (the real
T-2321 incident), every symref-less finding in that file was attributed
to whichever waiver happened to come first in the graph build, not the
comment actually nearest the finding it was meant to explain.
Suppression itself was never wrong (any matching waiver suppresses); this
is purely a display/attribution correctness gap.

Fix: `Edge.origin` already carries `"{path}:{lineno}"` for every parsed
directive (`dsl.py::_parse_line`, confirmed by reading it, not assumed)
-- added `_waiver_origin_line()` to parse it and `_closest_by_line()` as
the sort key. `_match_waiver`'s symref-less branch now collects ALL
matching candidates (instead of returning on the first hit) and, when
more than one matches, returns the one whose own comment line is
numerically CLOSEST to the violation's line. The symref-exact branch
(unaffected, already precise -- a symbol can only be one waiver's own
target) is unchanged.

Verified against a genuine repro: committed the repro tests alone
(c32b3d37a), confirmed the line-nearest test genuinely FAILS at that
commit against the pre-fix source (temporarily restored main's pre-fix
_waive.py and re-ran -- assertion failure showing the FAR waiver's reason
attributed to the NEAR violation, exactly the T-2321 incident shape),
restored the fix (d58a147ed), re-ran -- both new tests plus the existing
`test_match_waiver_prefix_reach_gated_to_package_scoped_rules` pass.
`--check-repro`/`--designate-repro` against base-ref c32b3d37a confirms
FAILED_AT_PARENT.

Changed:
- src/frob/gates/_waive.py::_waiver_origin_line (new)
- src/frob/gates/_waive.py::_closest_by_line (new)
- src/frob/gates/_waive.py::_match_waiver (symref-less branch now proximity-picks among all matches)

Evidence:
- tests/test_gates.py::TestTestGate::test_match_waiver_picks_line_nearest_of_two_same_file_same_rule (designated repro, FAILED_AT_PARENT @ c32b3d37a)
- tests/test_gates.py::TestTestGate::test_match_waiver_still_suppresses_regardless_of_which_one_wins

Filed: none.

### Changed
```
 src/frob/gates/_waive.py | 52 ++++++++++++++++++++++++---
 tests/test_gates.py      | 92 ++++++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2338/ticket.md |  9 +++--
 3 files changed, 147 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_match_waiver_picks_line_nearest_of_two_same_file_same_rule` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_match_waiver_still_suppresses_regardless_of_which_one_wins` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2338/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2338, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
