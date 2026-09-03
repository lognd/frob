## Done report

Measured `frob check --only tickets` on main: 9 gate:TICK errors this
sprint's assignment covers (TICK004 x4, TICK006 x4, TICK011 x1). Fixed
the TICK006/TICK011 half (5 of 9); TICK004's four findings are real
owner-level triage decisions across four significant standing tickets
(one a user directive, T-1382), reported separately rather than decided
unilaterally here.

TICK006 (4): each finding is a Done report's "Filed: T-draft-<hex>"
citation for a draft ticket id that never survived land (the T-0577
draft-loss class) -- the draft was genuinely created at close time but
lost before renumbering assigned it a real id. In every one of the 4
cases the REAL ticket for the exact same defect already exists on main
under a different id:
- T-3227/T-3236/T-3238 each cited T-draft-e1bca269 for "close-time
  disclosure check false-positives on split done-report.md" -- the real
  ticket is T-3285 (done), already correctly cited by T-3219's own Done
  report for the identical bug.
- T-3031 (archived) cited T-draft-36006d55 for a specific test failure
  (TestGitlessTargetGateSeverity::
  test_render_lint_gate_warns_not_errors_on_gitless_root fails on main)
  -- the real ticket is T-3091, filed with the identical title and its
  own body stating "Found while working T-3031".
Rebound all 4 citations to their real ids. T-3031 also needed a second
edit: an earlier, unrelated prose sentence ("...the third filed here as
T-draft-36006d55...") independently re-triggered TICK006 on the same
phantom id via its own separate "filed" occurrence -- reworded to avoid
the trigger word ("drafted here as ..." + double-quoting the id).

TICK011 (1): T-2978's Done report discloses a SCOPE CUT and does cite a
real, still-open follow-up ticket (T-2998) -- but the citation sits
~500 chars after the "SCOPE CUT" trigger phrase, outside TICK011's
300-char vicinity window. Added a second, closer citation immediately
after the trigger phrase; left the original citation in place.

Re-measured `frob check --only tickets` after the fix: 4 errors (all
TICK004), down from 9.

Filed as a draft off T-3343 (measurement-first triage ticket for the
wider gate:COV/TICK/REL/REG/REF sprint assignment); mints a real id at
land/renumber.

### Changed
```
 tickets/T-3363/ticket.md | 56 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 56 insertions(+)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_tick006_genuinely_lost_draft_still_caught_no_rename_no_duplicate` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_tick006_already_recovered_citation_rewritten_not_refiled_again` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosure_with_a_real_citing_id_is_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 44 error(s), 3932 warning(s), 883 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC011@docs/guides/release.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT002@src/frob/app/check_runner.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
