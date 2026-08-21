## Done report

Changed:
- src/frob/app/ticket_runner/_verify.py::_gates_stage_ran (new)
- src/frob/app/ticket_runner/_verify.py::_parse_error_findings_from_json (body: added the positive gate-summary-presence check, first, before every existing budget/incomplete-tool check)
- tests/unit/test_ticket_runner_gate_findings.py (new fixtures _NATIVE_STALENESS_ABORT_STDOUT / _DERIVED_STATE_ABORT_STDOUT, new tests test_native_staleness_abort_yields_none_not_the_abort_findings / test_other_pre_gate_abort_also_yields_none_not_only_native001, gate-summary entries added to the three TestParseErrorFindingsFromJsonDropsBlankIdentity fixtures that previously lacked one)
- docs/modules/tickets-landing.md (new section "A pre-gate abort can also hide as a clean, fully-measured run (T-2793)")

Root cause, confirmed by direct reproduction: `frob.check._native_staleness_result`/`_derived_state_integrity_result` and `frob.app.check_runner`'s opt-in `claude-config-drift` stage all run BEFORE the gates stage and, on failure, return a `CheckResult` containing ONLY their own `ToolResult`(s) -- no `"budget"` key, and every `ToolResult` legitimately fails WITH a real error diagnostic, so neither T-1703's `_budget_deferred_stage_groups`, T-2713's `_budget_skipped_groups_from_payload`, nor T-2521's `_incomplete_tool_results` can distinguish this from a genuinely complete run that happened to find exactly those findings. `_gates_stage_ran` (`_find_tool_result(results, "gate-summary") is not None`) is a positive assertion, not one more enumerated abort case: `_parse_error_findings_from_json` now refuses (returns `None`, unmeasured) whenever the gates stage itself never produced its own summary row, before any other check runs.

_rapid_sweep.py itself needed NO changes: it already treats `_unscoped_error_findings(...) is None` as `RapidSweepError.Unmeasurable` (no baseline write, no watermark advance, a loud `_log.error`) -- the gap was entirely that the shared parser in `_verify.py` handed it a false non-None frozenset for an aborted run. Ticket scope was widened (with `frob ticket scope --add` + recorded reason, mirrored to main) from the originally-declared `_rapid_sweep.py`-only scope to include `_verify.py` (the true fix location), its own test file, and the doc section, once tracing the abort JSON shape upstream confirmed the parser -- not the sweep -- was the actual gap.

Positive controls proven, both directions:
- NATIVE001 fast-exit -> `None` (test_native_staleness_abort_yields_none_not_the_abort_findings). Repro DESIGNATED and verified genuinely FAILED_AT_PARENT (commit 9acfdc36f, test-only commit before the fix landed on top of it) via `frob ticket evidence --check-repro`.
- A DIFFERENT pre-gate abort, DERIVED001 (never NATIVE001-specific) -> `None` (test_other_pre_gate_abort_also_yields_none_not_only_native001) -- proves the fix asserts on the positive signal, not a named reason.
- A genuine complete run (real `"gate-summary"` present) still measures its real findings exactly as before -- covered by the pre-existing test_ty_and_gate_error_both_appear_in_parsed_set (cited, not duplicated -- an identical second test would be DUP001).
- A `--budget`-truncated run is still caught (T-2713 non-regression) -- covered by the pre-existing test_budget_truncated_run_yields_none_not_a_partial_set / test_resume_narrowed_run_yields_none_not_a_partial_set, both still green.

Evidence: 5 pytest node ids bound (see `frob ticket show T-2793`), designated repro = test_native_staleness_abort_yields_none_not_the_abort_findings, FAILED_AT_PARENT confirmed against 9acfdc36f.

Filed: none. The separate native-staleness PERMANENT LATCH defect (src/frob/strata/_native_staleness.py:305's content-digest branch never refreshing its stamp even after a genuine, reproducible `maturin --release` rebuild) is reported per the dispatcher's instruction but deliberately NOT filed as a new ticket by me -- the dispatcher asked for a disposition, and my disposition is: this is real, separate, and already fully described with a live repro (delete `.frob/native-content-stamps.json` re-baselines to 0, and the latch re-forms on the next unrelated source edit); whoever coordinates this drive should file it, since I do not have standing measurement beyond what was handed to me and filing it myself would just restate the dispatch note as a ticket.

Gates: `frob check --ticket T-2793` clean of anything new -- the 30 error / 24-identity output present both before and after this change is pre-existing repo floor (CYCLE001, COV001/COV003, DOC006, DRIFT001/DRIFT002 on unrelated files, PERF004, REG002, SEC110, SYS003, TEST001, TICK003/TICK004, CLAUDE001 -- none touch this ticket's scope). No frob:waive needed.

### Changed
```
 docs/modules/tickets-landing.md                |  51 +++++++++
 frob.lock                                      |  20 +++-
 src/frob/app/ticket_runner/_verify.py          |  87 ++++++++++++++-
 tests/unit/test_ticket_runner_gate_findings.py | 141 ++++++++++++++++++++++++-
 tickets/T-2793/ticket.md                       |  56 +++++++++-
 5 files changed, 348 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_native_staleness_abort_yields_none_not_the_abort_findings` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_other_pre_gate_abort_also_yields_none_not_only_native001` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_ty_and_gate_error_both_appear_in_parsed_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_budget_truncated_run_yields_none_not_a_partial_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_resume_narrowed_run_yields_none_not_a_partial_set` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 18 error(s), 1093 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2793, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
