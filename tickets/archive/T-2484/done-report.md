## Done report

Changed:
src/frob/__main__.py::_report_concurrent_check_advisory_best_effort
src/frob/__main__.py::_dispatch

Fix: `_report_concurrent_check_advisory_best_effort` now takes a
`force_stderr` keyword. `_dispatch` passes `force_stderr=True` exactly
when `--json` was parsed on a `check` invocation. When `force_stderr` is
set, the advisory bypasses the module logger entirely and `print`s
straight to `sys.stderr` (mirroring `_print_startup_warnings`'s own
established idiom in the same file) instead of going through
`_log.info`/`_log.warning`. This was necessary, not cosmetic: the first
fix attempted (`frob.logging.quiet.quiet_stdout_logs()` around the call)
raised the shared stdout handler's level for the duration of the call,
which stopped the corruption but ALSO made the below-four (INFO-level)
case vanish from stderr too, since `config.toml`'s stderr handler only
accepts WARNING+. `--json` at low-concurrency counts would have gone
completely silent -- failing acceptance [1]. The direct-print approach
avoids the level-based routing altogether so the message reaches stderr
regardless of the INFO/WARNING split, in every case.

The non-`--json` path is unchanged: still the original level-routed
`_log.info`/`_log.warning` calls, so existing `caplog`-based tests and
behavior are untouched.

Other stdout-when-`--json` audit (acceptance [4]'s adjacent ask, scoped
to `src/frob/__main__.py`): every `print()` call in this file already
targets `sys.stderr` (`_print_startup_warnings`'s three warnings, the
KeyboardInterrupt/exception handlers). No other stdout leak found within
this file's scope. A structural "--json suppresses all non-JSON stdout
at the boundary" guard was considered (per the ticket's third ask) but
not built here: the single real offender was this one advisory, already
fixed at its source without needing a boundary-wide interceptor, and a
repo-wide boundary guard touches files outside this ticket's declared
scope (`check_runner.py`'s `run()` and its many `--json`-aware stages) --
filing a follow-up for that broader structural guard rather than
expanding scope.

_parse_check_json None-handling audit (acceptance [3], per caller):
  - `src/frob/app/ticket_runner/_verify.py` (the `fn()` closure inside
    the check-spawning factory, ~line 826): `data is None` -> logs a
    WARNING ("gate state is unmeasured, not zero") and returns `None`.
    CORRECT -- treated as not-measured.
  - `src/frob/app/ticket_runner/_verify.py::_budget_deferred_groups_from_stdout`
    (~line 965): `data is None` -> returns `()` (empty tuple). This is
    NOT a "measured zero findings" claim -- it only reports "no BUDGET001
    deferral names recoverable," a strictly additive detail queried
    alongside (never instead of) the real measured/unmeasured verdict
    from `_parse_error_findings_from_json`/`_parse_error_findings_from_stdout`
    elsewhere. Reviewed and judged CORRECT as-is; no change needed.
  - `src/frob/app/ticket_runner/_verify.py::_parse_error_findings_from_stdout`
    (~line 1111): on `_parse_check_json` returning `None`, this function
    falls through to a LEGACY plain-text parser (`## Errors` heading +
    `_GATE_SUMMARY_COUNTS_RE`), by design, for the ONE caller
    (`_close_cmd`'s T-1399 check) that still spawns non-JSON `frob
    check`. Traced whether a T-2473-corrupted `--json` stdout could be
    misread as valid legacy text: the corruption prefix is
    `"frob check: N other check(s) already running..."`, which contains
    neither `"## Errors"` (only ever emitted by the plain-text renderer,
    `frob.check._section_lines`) nor the literal `"gate-summary "` +
    digit-count phrase `_GATE_SUMMARY_COUNTS_RE` requires (the JSON
    payload's `"tool": "gate-summary"` and `"summary": "N errors, ..."`
    are separate JSON keys, never concatenated as that literal phrase).
    Confirmed empirically too: the corrupted-JSON reproduction command in
    the ticket's own repro, run through this function, hits the legacy
    path's own "no parsable gate-summary line" branch and returns `None`
    -- CORRECT, still unmeasured, not silently zero.
  - `src/frob/app/ticket_runner/_rapid_sweep.py::_matching_error_diagnostics`
    (~line 1061): `data is None` -> logs a WARNING ("treating as
    unmeasurable") and returns `None`. CORRECT -- treated as not-measured,
    docstring explicit that `None` is never conflated with an empty list.

CONCLUSION for acceptance [3]: no caller of `_parse_check_json` was found
that conflates a decode failure with "measured, nothing found." The
critical concern raised in the ticket -- that a land running during
concurrent-check load might have been silently unverified since T-2473
landed -- does NOT hold: every path this audit reached ends in an
explicit unmeasured signal (`None`/logged WARNING), never a false clean.
No caller needed correction.

Positive controls run:
  - must-now-parse (acceptance [0]): with a genuine second `frob check`-
    named process alive on the host (verified via the real
    `count_running_checks` scan, others=3 in one run since this host
    also had live fleet activity), `uv run frob check --json --only fmt`
    stdout parsed as clean JSON with zero prefix stripping.
  - must-still-advise (acceptance [1]): same run's stderr contained the
    full advisory line ("N other check(s) already running...").
  - must-stay-quiet (acceptance [2]/[3] semantics on an idle count):
    `test_force_stderr_idle_machine_stays_quiet` monkeypatches
    `count_running_checks` to 0 and asserts BOTH streams are empty (a
    genuinely idle *host* could not be produced on this shared machine,
    which had real concurrent fleet activity throughout this session --
    the monkeypatched unit test is the deterministic substitute, same
    technique the pre-existing T-2473 tests in this file already use).

Evidence:
tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_writes_to_stderr_not_stdout (accepts 0)
tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_below_four_still_reaches_stderr (accepts 1)
tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_idle_machine_stays_quiet (accepts 2)
tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_dispatch_passes_force_stderr_only_for_json (accepts 0, 1)

Filed: none

Gates: `frob check --ticket T-2484` clean of new errors on
`src/frob/__main__.py` (repo-wide gate-summary counts are pre-existing,
per the command's own gate:scope-note -- verified no diagnostic in the
`--json` output names `__main__.py`). `frob fmt --check` clean. Full
`TestConcurrentCheckAdvisory` class: 8/8 pass.

Additional evidence for acceptance [3] (added tests/unit/test_check_json_none_handling_t2484.py,
new file, exercises but does not modify the out-of-scope callers):
tests/unit/test_check_json_none_handling_t2484.py::TestParseCheckJsonReturnsNoneOnCorruption::test_corrupted_json_stdout_is_unparsable (accepts 3)
tests/unit/test_check_json_none_handling_t2484.py::TestBudgetDeferredGroupsFromStdoutOnNone::test_corrupted_stdout_yields_empty_tuple_not_a_false_claim (accepts 3)
tests/unit/test_check_json_none_handling_t2484.py::TestParseErrorFindingsFromStdoutOnCorruption::test_corrupted_json_stdout_is_unmeasured_not_empty (accepts 3)
tests/unit/test_check_json_none_handling_t2484.py::TestMatchingErrorDiagnosticsOnNone::test_none_data_returns_none_not_empty_list (accepts 3)

### Changed
```
 tickets/T-2484/done-report.md | 127 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2484/ticket.md      |  33 +++++++++--
 2 files changed, 154 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_writes_to_stderr_not_stdout` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_below_four_still_reaches_stderr` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_idle_machine_stays_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_dispatch_passes_force_stderr_only_for_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_json_none_handling_t2484.py::TestParseCheckJsonReturnsNoneOnCorruption::test_corrupted_json_stdout_is_unparsable` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_json_none_handling_t2484.py::TestBudgetDeferredGroupsFromStdoutOnNone::test_corrupted_stdout_yields_empty_tuple_not_a_false_claim` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_json_none_handling_t2484.py::TestParseErrorFindingsFromStdoutOnCorruption::test_corrupted_json_stdout_is_unmeasured_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_json_none_handling_t2484.py::TestMatchingErrorDiagnosticsOnNone::test_none_data_returns_none_not_empty_list` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2484/src/frob/app/ticket_runner/_waive_audit.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2484, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, invalid-argument-type@tests/unit/test_check_json_none_handling_t2484.py
