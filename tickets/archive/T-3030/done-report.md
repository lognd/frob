## Done report

Changed:
src/frob/check/__init__.py::_STAGE_GROUPS

Evidence:
tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool

Premise: held exactly as filed, confirmed by direct measurement (`frozenset()` diff between `_STAGE_GROUPS`' union and `frob.gates._ALL_GATES`). All four named gates -- milestone, env_var_docs, root_asset_dirs, profile_boundary -- were genuinely absent from every `_STAGE_GROUPS` member, making them unreachable via `--only <stage>` looping (the documented FROB_AGENT foreground-budget pattern). The ticket's own designated repro test, `tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool`, was already the failing test at parent -- confirmed FAILED_AT_PARENT via `frob ticket evidence --designate-repro`.

Found while root-causing (not part of the named four, same fix/same commit): `narrative_blocks` (NARR001) has the identical omission shape and was also missing from every stage group. Included in this same fix rather than filed separately -- it is the same symbol (`_STAGE_GROUPS`), same defect class, same test.

Fix: added all five (`milestone`, `env_var_docs`, `root_asset_dirs`, `profile_boundary`, `narrative_blocks`) to the `gates-fast` group -- verified none is in `frob.gates._PROCESS_POOL_GATES` (all thread-pool, sub-second gates), matching every other entry in that group and the precedent comments already there for `ffi_boundary`/`suppress` (T-1044/T-1340, the identical registered-but-unreachable shape).

Verified each is now reachable: `frob.check._expand_stage_groups({'gates-fast'})` contains all five. `--only gates-fast` (and by extension `frob check`'s default full run) now reaches them.

Gates: `tests/system/test_cli_check.py::TestCheckStageGroups` (4 tests) all green. Full `tests/system/test_cli_check.py` run: 3 pre-existing, unrelated failures (`TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses`, `TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root`, `TestCheckPolyglot::test_pinned_check_type_reports_skipped_line`) -- all three fail on host-load contention ("3 other check(s) already running on this host") or a stale native-cache error unrelated to `_STAGE_GROUPS`, reproduced identically across two consecutive runs, none touching `_STAGE_GROUPS` or the stage-group mechanism.

### Changed
```
 tickets/T-3030/ticket.md | 12 +++++++++++-
 1 file changed, 11 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
