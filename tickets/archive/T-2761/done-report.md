## Done report

Changed:
src/frob/app/fmt_runner.py::run
src/frob/app/ticket_runner/_land_cmd.py::_fmt_pre_land_step
src/frob/gates/_fix_engine_text.py::_fmt001_scoped_fixes
src/frob/gates/_fix_engine_text.py::fix_fmt001_directive_wrap
src/frob/gates/_todo_fmt.py::fmt_gate
src/frob/gates/_todo_fmt.py::_fmt001_file

All four callers T-2761 named (frob fmt CLI, land's absorbed fmt step,
the Tier-A FMT001 auto-fix handler, and the FMT001 diff gate) stopped
pre-resolving one ruff-derived read_line_length(root) limit and passing
it as an explicit format_paths(..., limit=...) override, which had been
short-circuiting T-1606's per-file resolve_line_length resolution by
design. Three callers (fmt_runner, _land_cmd, _fix_engine_text) simply
drop the limit= kwarg so format_paths's own default takes over. The
fourth (_todo_fmt.fmt_gate) did not call format_paths at all -- it
independently derived one project-wide limit for its own diff-scoped
length check -- so it now calls resolve_line_length(root / file, root)
per touched file instead, and _fmt001_file treats a None result
(a language with no configurable width) as "never flag".

Evidence: pytest node ids bound directly (ticket carries no acceptance
items to key off of):
tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmtRunnerReachability::test_check_mode_reports_no_change_for_rust_file_under_its_own_width
tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmtRunnerReachability::test_write_mode_leaves_rust_directive_untouched
tests/unit/test_fmt_wiring_reachability_t2761.py::TestLandFmtStepReachability::test_touched_scoped_step_leaves_rust_file_untouched
tests/unit/test_fmt_wiring_reachability_t2761.py::TestLandFmtStepReachability::test_whole_tree_fallback_leaves_rust_file_untouched
tests/unit/test_fmt_wiring_reachability_t2761.py::TestTierAFixHandlerReachability::test_scoped_fix_reports_no_applied_fix_for_rust_file
tests/unit/test_fmt_wiring_reachability_t2761.py::TestTierAFixHandlerReachability::test_whole_tree_fix_reports_no_applied_fix_for_rust_file
tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmt001GateReachability::test_rust_file_over_ruff_width_but_under_rustfmt_width_not_flagged
tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmt001GateReachability::test_rust_file_over_its_own_rustfmt_width_still_flagged

Each entrypoint is proven end to end against a fixture with ruff
line-length=20 and rustfmt.toml max_width=200: a directive comment over
20 columns but under 200 is left untouched through the real caller
(reachability), and the last test is a positive control -- the SAME gate
still fires when the directive genuinely exceeds its OWN (narrowed)
rustfmt width, proving this is real per-file resolution and not a
detector that stopped firing.

Filed: none

Gates: frob check --ticket T-2761 clean of new findings -- the 25 errors
remaining after this change are pre-existing baseline noise (CYCLE001
import cycle, unrelated COV001/COV003/DOC006/DRIFT001/DRIFT002/SEC110/
TEST001/TICK003/TICK004/CLAUDE001 findings), none touching the files this
ticket changed.

### Changed
```
 tickets/T-2761/ticket.md | 26 +++++++++++++++++++++++++-
 1 file changed, 25 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmtRunnerReachability::test_check_mode_reports_no_change_for_rust_file_under_its_own_width` (pytest node id, verified passing when recorded)
- `tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmtRunnerReachability::test_write_mode_leaves_rust_directive_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_fmt_wiring_reachability_t2761.py::TestLandFmtStepReachability::test_touched_scoped_step_leaves_rust_file_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_fmt_wiring_reachability_t2761.py::TestLandFmtStepReachability::test_whole_tree_fallback_leaves_rust_file_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_fmt_wiring_reachability_t2761.py::TestTierAFixHandlerReachability::test_scoped_fix_reports_no_applied_fix_for_rust_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_fmt_wiring_reachability_t2761.py::TestTierAFixHandlerReachability::test_whole_tree_fix_reports_no_applied_fix_for_rust_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmt001GateReachability::test_rust_file_over_ruff_width_but_under_rustfmt_width_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmt001GateReachability::test_rust_file_over_its_own_rustfmt_width_still_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 16 error(s), 1320 warning(s), 710 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
