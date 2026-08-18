## Done report

Changed:
src/frob/app/check_runner.py::_StderrRedirectStdout
src/frob/app/check_runner.py::_StderrRedirectStdout.write
src/frob/app/check_runner.py::_StderrRedirectStdout.flush
src/frob/app/check_runner.py::_StderrRedirectStdout.__getattr__
src/frob/app/check_runner.py::_guard_json_stdout_writes
src/frob/app/check_runner.py::run
src/frob/app/check_runner.py::_run_stages_and_report
src/frob/app/check_runner.py::_try_check_delta_via_daemon
src/frob/app/check_runner.py::_run_land_parity
src/frob/app/check_runner.py::_run_census
src/frob/app/check_runner.py::_run_ruff_fix_mode

Fix (structural, not per-instance): `_guard_json_stdout_writes` is a new
context manager that, for its duration, replaces `sys.stdout` with
`_StderrRedirectStdout` -- a proxy whose `write`/`flush` redirect to the
REAL `sys.stderr` (captured once at guard entry) and whose every other
attribute access (encoding, `isatty()`) delegates transparently to the
real stdout. This is a strict superset of `quiet_stdout_logs` (which
only raises the shared root-logger stdout handler's LEVEL, so it
protects a misleveled log call but does nothing for a bare
`print()`/`sys.stdout.write()`): with this guard active, NO write of any
shape anywhere in the guarded call stack can reach the real stdout,
present code or future.

Applied at every risky span this ticket's scope reaches in
`check_runner.py`: `run`'s lease/stamp-mode block (replacing the old
`quiet_stdout_logs`/`nullcontext` choice), `_try_check_delta_via_daemon`'s
RPC query+reconcile, `_run_stages_and_report`'s stage-run + `--fix`
reverify, `_run_land_parity`'s `land_parity_findings` spawn+parse,
`_run_census`'s gate run, and `_run_ruff_fix_mode`'s `_run_ruff_autofix`
spawn. In every case the guard is closed BEFORE that function's own
final `_log.info`/`_log.error`/`_print_census` payload write, so the
one legitimate write always reaches the real stdout via the existing
`_LazyStdoutHandler` (unchanged mechanism, unchanged bytes).

Existing instances audited (acceptance-adjacent ask, "report the count
even if zero"): grepped every `print(` call in `check_runner.py` --
ZERO found before this ticket. The class of leak this ticket closes was
never a literal `print()` in this file; it is the STRUCTURAL gap (a
misleveled log call, or a future print, anywhere in the guarded call
stack) the guard now closes regardless of shape.

Subcommand enumeration (acceptance [3]): every `--json`-bearing CLI flag
repo-wide, via `src/frob/_cli_parsers/`: 27 distinct `dest=` names
across 53 `add_argument` call sites (arch_json, bind_json, check_json,
clean_json, debt_json, deprecated_json, docs_json, doctor_json,
dup_json, exports_json, fleet_json, fmt_json, gitlog_json, graph_json,
map_json, mutate_json, outline_json, parse_json, perf_json,
profile_json, registry_json, stats_json, test_json, ticket_json,
verify_json, vet_json, xref_json). `check` (`check_json`) is the ONLY
one this ticket protected -- its scope is `check_runner.py` alone. Filed
T-2492 to audit the other 26 for the same unguarded-write class (do not
assume they are safe just because none is proven leaking yet -- T-2484's
own leak sat unnoticed for minutes before fleet load exposed it).

Doc-touch note: `run`/`_run_census`'s own `docs/modules/app.md#runners`
affects()-closure doc could not be updated in this diff -- that file is
held by T-2485's LIVE cross-worktree scope lease (`ScopeLeaseConflict`
on `--add`). Waived AFFECT001 at both sites with a reason naming T-2491,
filed to do that doc sync once the lease clears. `_run_land_parity`'s
own doc target, `docs/modules/tickets-landing.md`, was NOT leased --
added a real paragraph there describing the guard, satisfying AFFECT001
with content, not a waiver.

Positive controls (all run via `tests/unit/test_app_runners_batch6.py`,
in-process, using a NEW `_real_console_handlers` fixture that installs
frob's real `_LazyStdoutHandler`/`_LazyStderrHandler` pair on the root
logger for the test's duration -- under plain pytest, `frob.logging.
logger._init` installs ZERO handlers, T-1621, so `_log.info` output
never physically touches `sys.stdout`/`capsys` even though `caplog`
still sees the record; these tests need the REAL physical write to
prove the guard, not merely that a log record was produced):
  - must-now-protect (acceptance [0]): `test_planted_print_inside_json_
    run_does_not_corrupt_payload` monkeypatches `run_check` to `print()`
    a deliberately planted leak mid-execution, then calls `check_run`
    with `--json` -- asserts the leak text is absent from `captured.out`
    and that `captured.out` still parses as valid JSON with a
    `"results"` key. This is exactly the shape T-2484's own leak took
    (a write from inside the guarded span, not from the final report
    call), planted as a real fixture rather than a synthetic one, per
    the ticket's own instruction.
  - must-still-inform (acceptance [2]): `test_planted_print_still_
    reaches_stderr` asserts the SAME planted text appears in
    `captured.err` -- the guard redirects, never swallows.
  - must-still-emit (acceptance [1]): `test_legitimate_json_payload_is_
    byte_identical_with_guard_active` asserts the real payload (parsed
    from `captured.out`) is unchanged from the pre-guard shape --
    `_make_check_result`'s fixed `results` list, byte-for-byte, with
    nothing planted. `test_no_planted_print_no_stderr_noise` is the
    idle-machine corollary: with nothing planted, the guard itself adds
    no stderr noise.
  - acceptance [3]: `test_more_than_one_subcommand_has_a_json_mode`
    locks the 27-destination enumeration finding as a regression test
    (floor of 20, not an exact count, so it does not need updating for
    every future unrelated `--json` flag) and asserts `check_json` is
    among them.

Evidence:
tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_planted_print_inside_json_run_does_not_corrupt_payload (accepts 0)
tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_legitimate_json_payload_is_byte_identical_with_guard_active (accepts 1)
tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_planted_print_still_reaches_stderr (accepts 2)
tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_no_planted_print_no_stderr_noise (accepts 1)
tests/unit/test_app_runners_batch6.py::TestJsonSubcommandEnumeration::test_more_than_one_subcommand_has_a_json_mode (accepts 3)

Filed: T-2491 (docs/modules/app.md#runners sync, blocked on T-2485's
lease), T-2492 (audit the other 26 --json runners for the same class).

Gates: `frob check --ticket T-2486` clean of new errors on
`src/frob/app/check_runner.py`, `tests/unit/test_app_runners_batch6.py`,
`docs/modules/tickets-landing.md` (repo-wide counts elsewhere are
pre-existing/unscoped noise per the command's own gate:scope-note).
`frob fmt --check` clean. Full `TestJsonStdoutStructuralGuard` +
`TestJsonSubcommandEnumeration`: 5/5 pass. Confirmed the three unrelated
`tests/system/test_cli_check.py` failures encountered mid-work
(`test_skip_exports`, `test_available_stages_cover_every_gate_and_tool`,
`test_clean_code_exits_zero`) reproduce identically against an
UNMODIFIED `check_runner.py` (verified by checking the file out and
re-running) -- pre-existing repo-wide drift (a new schema-declaration
gate requirement), not caused by this ticket; not touched, per scope.
Waived: AFFECT001 at `run`/`_run_census` (T-2491, lease conflict);
OPAQUE001 at `_StderrRedirectStdout.__getattr__`/its one call site
(deliberate pass-through delegator, documented); WIRE001 at
`_real_console_handlers` (T-2486, pytest fixture consumed via
injection, not a direct call the static resolver sees).

### Changed
```
 tickets/T-2486/ticket.md | 36 +++++++++++++++++++++++++++++++-----
 1 file changed, 31 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_planted_print_inside_json_run_does_not_corrupt_payload` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_legitimate_json_payload_is_byte_identical_with_guard_active` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_planted_print_still_reaches_stderr` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_no_planted_print_no_stderr_noise` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestJsonSubcommandEnumeration::test_more_than_one_subcommand_has_a_json_mode` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2486/src/frob/app/ticket_runner/_waive_audit.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2486, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
