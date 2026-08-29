## Done report

Root cause found and fixed: T-2718's "## Done report" structural-subheading
signal (signal 2 of `disclosure_shaped_language`) scans EVERY line matching
`^#{2,6}[ \t]+\S.*$` in the Done-report section, including lines INSIDE a
fenced code block. `compose_done_report`'s own Tier-A-generated "### Changed"
section fences `git --stat` output verbatim (`render_changed_block`), so a
changed-path line, or any other verbatim-quoted text elsewhere in the report,
that happens to start with 1-6 literal '#' characters was misread as a real
markdown subheading -- exactly the reported false positive on a Tier-A
"### Changed" subheading. Reproduced directly against the real
`disclosure_shaped_language` with a minimal fenced-line input
(`tests/unit/test_reporting_t3285_fenced_subheadings.py`); confirmed the
un-fence-aware scan flags it and the fixed one does not.

Fix: added `_subheading_titles_outside_fences`, a fence-tracking scan that
never treats a line inside a triple-backtick-delimited span as a markdown
heading -- this is a parsing fix (the check now respects CommonMark's own
rule that fenced content is not re-parsed as block structure), not a policy
change: `_DISCLOSURE_PHRASES` and `_TIER_A_GENERATED_SUBHEADINGS` are
untouched, and a genuine hand-typed subheading outside any fence still fires
exactly as before (regression-tested).

SEQUENCING: T-3272 (ledger v2 default for new scaffolds) landed on main
BEFORE this ticket finished -- observed via `frob ticket show T-3272` (state
done) and a `git rebase main` that picked up its land commit partway through
this ticket's work. This fix lands AFTER T-3272, not before/with it as
requested; the affected window is real (new-repo `frob ticket close` on a
Tier-A-generated split done-report between T-3272's land and this one).
Flagging for the coordinator rather than silently noting it.

Also verified: the direct REPL-reported "merge + check returns None"
disagreement is NOT explained by a double-splice or cache-staleness bug in
`_merge_sibling_done_report`/the v2 index cache -- traced both the
`load_all` -> `_merge_sibling_done_report` path and a
load-modify-write_ticket round trip (`_write_ticket_v2_mode` /
`_split_done_report`) with reproduction scripts; both round-trip cleanly
with no duplication. The disagreement is fully explained by the fenced-
code-block parsing gap above: the REPL check in the ticket's own
investigation almost certainly used report text without an offending
fenced line, while the live failure's Changed/Evidence block did.

Filed: none -- no further follow-up needed; the fix is scoped and complete.

### Changed
```
 src/frob/tickets/_reporting.py                     | 62 +++++++++++++++++---
 .../test_reporting_t3285_fenced_subheadings.py     | 67 ++++++++++++++++++++++
 tickets/T-3285/ticket.md                           | 15 ++++-
 3 files changed, 136 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_reporting_t3285_fenced_subheadings.py::TestSubheadingTitlesOutsideFences::test_hash_line_inside_fence_not_a_subheading` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t3285_fenced_subheadings.py::TestSubheadingTitlesOutsideFences::test_real_subheading_after_a_fence_still_detected` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t3285_fenced_subheadings.py::TestSubheadingTitlesOutsideFences::test_unterminated_trailing_fence_swallows_rest` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t3285_fenced_subheadings.py::TestDisclosureShapedLanguageFencedChanged::test_stat_line_starting_with_hash_inside_changed_block_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t3285_fenced_subheadings.py::TestDisclosureShapedLanguageFencedChanged::test_genuine_subheading_outside_fence_still_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 79 error(s), 3984 warning(s), 885 waived
- error-findings: AFFECT001@src/frob/tickets/_reporting.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-3262/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOCENUM001@docs/modules/gates.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
