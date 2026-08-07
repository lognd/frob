## Done report

Review round 2 (coordinator/reviewer REJECT): fixed all five required items
plus investigated the Changed-section report.

1. Deterministic, ticket-scoped gate claim: `DoneReportClaims` now carries
`gate_errors`/`gate_warnings`/`gate_waived` as structured ints, never the
raw `frob check` summary LINE (whose trailing `[archgate=7.99s, ...]`
per-gate timing blob is wall-clock and therefore different on every single
invocation, even against an identical tree -- this was the FATAL: strict
equality against that line refused every land, including this ticket's
own). `_check_gates_summary_fn` (ticket_runner.py) now parses the
`gate-summary` line's leading counts via a dedicated regex and discards
everything after it. Land's re-verification (`_reverify_done_report_
claims_post_merge`) compares ONLY `gate_errors` (the real pass/fail
signal); `gate_warnings`/`gate_waived` are captured and rendered for a
human reader but never gate the land, since repo-global warning/waived
counts legitimately move on a busy shared branch for reasons unrelated to
this ticket's own work (the parenthetical the reviewer flagged).

2. End-to-end test with REAL closures: added
`TestDoneReportThenLandRealClosuresEndToEnd.test_real_closures_done_
report_then_land_succeeds` in tests/test_ticket_land.py -- imports the
actual `_run_tests_count_fn`/`_check_gates_summary_fn`/`_land_passed_fn`/
`_land_collected_fn` from `frob.app.ticket_runner` (no fakes), builds a
minimal fixture repo with one real passing pytest test, drives it through
`transition` -> `sweep_ticket` -> `set_done_report` (real closures) ->
commit -> `land` (real closures), and asserts the land succeeds. This is
the test that would have caught the FATAL immediately -- it failed before
the round-2 fix (two real `frob check` spawns against an identical tree
produced different summary-line text) and passes after it. Runs in ~3s.

3. Derive land's test count from D-05's own `passed()` run:
`_reverify_evidence_post_merge` now returns `Ok(passing_ids)` (the exact
`frozenset` `passed()` produced) instead of `Ok(None)`, and
`_reverify_done_report_claims_post_merge` takes that set directly instead
of its own `run_tests` parameter -- `land`/`_land_locked` no longer accept
a `run_tests` callable at all (only `check_gates`); a `run_tests`-supplying
land no longer pays for a second collect+run of the same evidence ids.

4. Prework staleness ordering: `_refresh_prework_sweep(worktree, ticket)`
now runs BEFORE `_reverify_evidence_post_merge`/`_reverify_done_report_
claims_post_merge` (still gated on `dry_run_report is None`, i.e. only for
a real land, preserving the dry-run "leaves no trace" guarantee exactly as
before) instead of after both -- so `check_gates()`'s live `frob check
--ticket` spawn no longer observes a stale PRE001 caused by unrelated
main-side commits this same merge pulled in.

5. Anchored claim parsing: `parse_claims_from_done_report` now locates the
`### Captured claims` heading itself and only matches lines strictly
between it and the next `#`-heading (or section end) -- a free-prose
narrative line elsewhere in the Done report that happens to match either
regex's shape can no longer masquerade as a captured, re-verified claim.
Added `test_free_prose_elsewhere_never_masquerades_as_claims` and
`test_only_lines_inside_the_claims_heading_count` to lock this down.

Changed-section investigation: the earlier round's "(no changed files
detected)" was NOT a `compute_changed_lines`/worktree base-ref bug --
`frob ticket done-report` was run BEFORE the round-1 commit existed, so
`git diff --stat main...HEAD` correctly reported nothing (HEAD == main at
that moment; `set_done_report` never sees uncommitted working-tree
changes, only committed ones, which is `git diff main...HEAD`'s normal,
correct semantics). Verified by re-running the same `git diff --stat
main...HEAD` from the shell after committing round 1's changes: it
reports the full diff correctly. No code change needed; this Done report
(written after this round's commit) has a populated Changed section as
evidence the mechanism works as designed.

All five fixes are in this worktree, foreground, `uv run --frozen`. Not
closed, not landed, per instruction.

### Changed
```
 docs/modules/tickets.md                 |  34 ++++
 src/frob/app/ticket_runner.py           | 124 +++++++++++++-
 src/frob/tickets/__init__.py            |  74 +++++++--
 src/frob/tickets/_land.py               | 150 ++++++++++++++++-
 src/frob/tickets/_models.py             | 143 ++++++++++++++++
 tests/test_ticket_done_report_claims.py | 195 ++++++++++++++++++++++
 tests/test_ticket_land.py               | 285 ++++++++++++++++++++++++++++++++
 tickets.md                              | 112 ++++++++++++-
 8 files changed, 1096 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_round_trips_through_a_done_report_body` (pytest node id, verified passing when recorded)
- `tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_missing_section_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_omitted_when_no_callables_supplied` (pytest node id, verified passing when recorded)
- `tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_captured_from_real_callables` (pytest node id, verified passing when recorded)
- `tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_divergent_real_count_is_recorded_not_the_typed_narrative` (pytest node id, verified passing when recorded)
- `tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_gate_state_only_no_test_capture_leaves_claims_out` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_matching_claims_land_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_test_count_refuses_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_no_claims_section_skips_reverification` (pytest node id, verified passing when recorded)
- `tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_free_prose_elsewhere_never_masquerades_as_claims` (pytest node id, verified passing when recorded)
- `tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_only_lines_inside_the_claims_heading_count` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_warning_or_waived_count_alone_still_lands` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd::test_real_closures_done_report_then_land_succeeds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 15 evidence id(s))
- gates: 0 error(s), 1120 warning(s), 207 waived
