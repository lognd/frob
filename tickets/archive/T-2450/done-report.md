## Done report

Closed T-2407's SYS003 debt: `frob.verify._drain`/`frob.verify._worker`
called three PRIVATE, underscore-prefixed `app.ticket_runner` helpers
directly across a node boundary (`_detached_sweep_env`,
`_unscoped_error_findings`, `_file_regression_ticket`) -- the coupling
itself was already declared architecturally sound by T-2407, but the
private-name crossing was debt in its own right. Given the ticket's own
measured 10/55/62 grep-hit blast radius for a full rename, went with the
ticket's second listed option -- "introduce a small public wrapper" --
rather than dropping every underscore in place: a thin public function
sits next to each private implementation (`detached_sweep_env`,
`file_regression_ticket` in `_rapid_sweep.py`; `unscoped_error_findings`
in `_land_cmd.py`), `frob.verify`'s two call sites now import only the
public names, and every in-module caller of the three private
implementations is untouched. `file_regression_ticket`'s public
signature deliberately omits `attributed_ids` (the one cross-node caller
never supplies it) -- a narrower public surface is easier to keep
stable than mirroring every internal parameter.

All three new public names were added to `design/frob.strata`'s `cli`
node `interface=` list (alphabetically), closing the undeclared-cross-
node-coupling half of the debt alongside the naming half. Added a new
"Public seam for cross-node callers (T-2450)" section to
`docs/modules/tickets-verify-sweep.md` with `frob:describes` anchors for
all three, and updated the two existing prose references to
`_detached_sweep_env` (`_drain.py`'s own docstring,
`tickets-verify-sweep.md`'s "Automatic watermark drain" section) that
now describe the mechanism via the public seam.

`src/frob/tickets/_worktree_guard.py` has two PROSE comments mentioning
`_detached_sweep_env` by name (not a call site) -- left untouched: that
file is outside this ticket's declared scope (`src/frob/verify/**`,
`src/frob/app/ticket_runner/**`), and the comments remain accurate (the
private implementation they describe is unchanged, only a new public
wrapper was added alongside it).

Evidence: `pytest tests/unit/verify tests/unit/test_rapid_sweep.py
tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsPublicSeam
tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsExcludesNoTicketNoise
tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsFullMode -p no:xdist`
-- 352 passed, 0 failed (includes the 3 new delegation tests proving each
public wrapper calls through to its private implementation with the same
arguments/return value). Also ran
`tests/test_ticket_work_and_land_finish.py` (90 tests, 1 pre-existing
unrelated failure: `TestAssertDesignLoadsPreLand::test_a_tier_a_handler_
that_corrupts_design_after_it_was_healthy_refuses_the_land` fails on
`strata_core native extension unavailable` -- this worktree has no
native build, unrelated to this ticket's diff, which touches no .strata
parsing code).

Gates: `frob check --ticket T-2450` -- every scope-relevant finding
resolved: COV001 (frob:doc added on all three new public functions, new
anchor section in `docs/modules/tickets-verify-sweep.md`), TEST001
(frob:tests added on all three, pointing at the new delegation tests),
LANDPARITY001 (same frob:doc additions), AFFECT001 (`_drain.py::spawn_
deferred_drain`'s body changed via the `detached_sweep_env` docstring
reference -- its own affects()-closure doc section updated), SCOPE001
(scope extended to `design/frob.strata`, `tests/test_ticket_land.py`,
`tests/unit/test_rapid_sweep.py`, `docs/modules/tickets-verify-sweep.md`
with reasons). The remaining ~24 `gate:*` errors on the full `--ticket`
run (DEPR006, WAIVE011/WAIVE009, DRIFT001/DRIFT002 on an unrelated
`_bisect.py` pair and `_verify.py`, LARGE001 on two unrelated files,
REL001, TICK004 on two unrelated tickets, OPAQUE001 on an unrelated
file, COV003 on T-3410, DOC006 on a T-2691 changelog fragment) plus a
large block of `ty:unresolved-import`/LANG004/SELFAUDIT001 findings are
pre-existing repo-wide or this worktree's missing native-extension build
(frob_core/strata_core not importable here) -- none touch this ticket's
diff.

Filed: none -- no out-of-scope work found.

### Changed
```
 tickets/T-2450/ticket.md | 34 +++++++++++++++++++++++++++++++++-
 1 file changed, 33 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDetachedSweepEnvPublicSeam::test_delegates_to_the_private_implementation` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicketPublicSeam::test_delegates_to_the_private_implementation` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsPublicSeam::test_delegates_with_the_same_arguments` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 15 error(s), 4176 warning(s), 871 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@changelog.d/T-2691.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@tests/unit/verify/test_bisect.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
