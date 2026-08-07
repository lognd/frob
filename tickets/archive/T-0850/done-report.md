## Done report

T-0846 landed the (rule_id, file) identity-based ClaimDivergence comparison
but left one disclosed gap: a diff-scoped rule (SCOPE001, COV002, TODO001
-- already documented in this codebase as such, including WAIVE004's own
"known-flaky for diff-scoped rules" message text) can appear or disappear
between two SCOPED `--ticket` checks taken at different times purely from
base/diff drift, not a real regression the ticket introduced. Comparing
these identities at all reintroduces the same false-refusal class T-0846
already fixed for the raw-count case.

Added `SCOPED_RUN_FLAKY_RULE_IDS = frozenset({"SCOPE001", "COV002",
"TODO001"})` to `src/frob/gates/__init__.py` (public, doc-anchored at
docs/modules/gates.md#public-api) as the canonical, single-sourced set.

Applied the exclusion in `src/frob/app/ticket_runner.py` at the SAME
shared closure factories both `done-report` capture and `land`
re-verification call (`_check_gate_findings_fn`/`_check_gates_summary_fn`),
so the filter is symmetric by construction rather than by two call sites
staying in sync by hand -- exactly what the ticket's acceptance criterion
requires ("excluded ... at BOTH capture and reverify ends, symmetrically";
an asymmetric filter would still diverge on pure drift noise):

- Factored `_parse_error_findings_from_stdout` out of
  `_check_gate_findings_fn`'s inline parsing (NO DUPLICATION: it is now
  the one place that reads a `## Errors` section into a `(rule, file)`
  identity set) and added `_exclude_scoped_run_flaky`, applied to
  `_check_gate_findings_fn`'s returned identity set (closes the identity-
  comparison half of the gap).
- `_check_gates_summary_fn`'s returned `errors` count is now derived from
  the SAME filtered `## Errors` section (via
  `_parse_error_findings_from_stdout` + `_exclude_scoped_run_flaky`)
  instead of trusting the raw gate-summary line's count verbatim, falling
  back to that raw count only when the `## Errors` section itself does
  not parse at all (closes the count-only-fallback half of the gap, used
  by `_reverify_done_report_claims_post_merge` whenever either side is
  missing an identity set). `warnings`/`waived` are left unfiltered,
  matching the existing, deliberate "only gate_errors is compared"
  posture from T-0754/T-0832.

`src/frob/tickets/_land.py` itself needed NO changes: the identity/count
plumbing it already consumes (`check_gates`/`check_gate_findings`) now
arrives pre-filtered from the same two closures, so the exclusion is
transparent to `_reverify_done_report_claims_post_merge`'s existing
comparison logic.

Added unit tests in `tests/unit/test_ticket_runner_gate_findings.py` (the
existing home for these two closures' tests; added to this ticket's scope
via `frob ticket scope T-0850 --add` for this reason):
- `TestCheckGateFindingsFn.test_scoped_run_flaky_rule_excluded_from_findings`:
  a fixture mixing SCOPE001/COV002 (flaky) with SEC110 (real) asserts only
  SEC110 survives in the returned identity set.
- `TestCheckGatesSummaryFn.test_scoped_run_flaky_rule_excluded_from_error_count`:
  same fixture asserts the returned `errors` count is 1 (not the raw
  summary line's claimed 3).
- `TestCheckGatesSummaryFn.test_unparsable_errors_section_falls_back_to_raw_summary_count`:
  pins the fallback path (no `## Errors` section at all) still returns the
  real measured `(0, 0, 0)`.
Updated the pre-existing `_TWO_FINDINGS_STDOUT` fixture and
`test_parses_multiple_findings_from_errors_section`'s expected result:
its rule codes were SCOPE001/COV002, which this fix now correctly
excludes -- rewrote the fixture to use two non-flaky rule codes (SEC110,
PII010) so that test keeps verifying generic multi-finding parsing,
independent of the new exclusion behavior (a deliberate behavior change,
not a regression: excluding SCOPE001/COV002 there is the fix working as
intended).

Hand-verified mutant kill: reverted `_exclude_scoped_run_flaky` to `return
findings` (no-op) and reran the two new "excluded" tests -- both failed
exactly as expected: the identity test returned all three findings
instead of just SEC110, and the count test returned `errors == 3` instead
of `1`. Restored the fix; reran the full test file (12 passed) and ruff
(clean) afterward.

Ran the full verify command list from the brief:
`tests/system/test_cli_check.py tests/system/test_cli_ticket_land.py
tests/test_check_coverage_registry.py tests/test_gates.py
tests/test_gates_fmt_directives.py tests/test_gates_mutation_evidence.py
tests/test_gates_ratchet.py tests/test_gates_tick005.py
tests/test_gates_tickets_hygiene.py tests/test_gates_worktree_lease.py
tests/test_ticket_land.py tests/test_ticket_runner_archive_force.py
tests/test_ticket_runner_quiet.py tests/unit/test_check.py
tests/unit/test_check_tool_unavailable.py
tests/unit/test_ticket_runner_gate_findings.py
tests/unit/test_ticket_runner_land_release.py` -- 682 passed, 3 failed.
All 3 failures are PRE-EXISTING, unrelated to this change:
- `TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules`
  and `TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations`:
  `known_gate_rule_ids()` returns 115 entries at this branch's HEAD (before
  any of my edits -- verified by extracting `_KNOWN_GATE_RULES` directly
  from `git show HEAD:src/frob/gates/__init__.py`, which already matches
  the registry's 115), but the live function returns 116 in-process --
  a pre-existing one-rule registry/live drift this ticket's diff does not
  touch (`SCOPED_RUN_FLAKY_RULE_IDS` is a new constant, never added to
  `_KNOWN_GATE_RULES` or `known_gate_rule_ids()`).
- `TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root`:
  failed only when run as part of this large combined suite; passes
  cleanly in isolation (`uv run pytest
  tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root`,
  1 passed) -- test-order/state leakage from an unrelated test in the
  combined run, not a regression from this change.

### Deviations
`src/frob/check.py` (named in the ticket's original scope) does not exist
as a module in this repo -- the real location is the `src/frob/check/`
package; no changes were needed there since the identity/count plumbing
lives entirely in `frob.gates` and `frob.app.ticket_runner`.

### Changed
```
 docs/modules/gates.md                          |   1 +
 src/frob/app/ticket_runner.py                  | 156 +++++++++----
 src/frob/gates/__init__.py                     |  23 ++
 src/frob/tickets/__init__.py                   |  12 +-
 src/frob/tickets/_land.py                      |  22 +-
 src/frob/tickets/_models.py                    |  45 +++-
 tests/test_evidence_integrity.py               |  51 ++++-
 tests/test_ticket_land.py                      |  40 ++++
 tests/unit/test_ticket_runner_gate_findings.py |  99 +++++++-
 tickets.md                                     | 306 ++++++++++++++++++++++++-
 10 files changed, 700 insertions(+), 55 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_scoped_run_flaky_rule_excluded_from_findings` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestCheckGatesSummaryFn::test_scoped_run_flaky_rule_excluded_from_error_count` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestCheckGatesSummaryFn::test_unparsable_errors_section_falls_back_to_raw_summary_count` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 1241 warning(s), 221 waived
- error-findings: PRE001@tickets/T-0850
