## Done report

Changed:
src/frob/app/_json_guard.py (new)
src/frob/app/_json_guard.py::_StderrRedirectStdout
src/frob/app/_json_guard.py::_StderrRedirectStdout.write
src/frob/app/_json_guard.py::_StderrRedirectStdout.flush
src/frob/app/_json_guard.py::_StderrRedirectStdout.__getattr__
src/frob/app/_json_guard.py::_guard_json_stdout_writes
src/frob/app/check_runner.py::run (import updated to shared guard, no behavior change)
src/frob/app/bind_runner.py::run
src/frob/app/fmt_runner.py::run
src/frob/app/clean_runner.py::run
src/frob/app/docs_runner.py::_run_search
src/frob/app/docs_runner.py::_run_overview
src/frob/app/docs_runner.py::_run_extract
src/frob/app/vet_runner.py::_run_scan
src/frob/app/map_runner.py::_try_map_via_daemon
src/frob/app/map_runner.py::run
src/frob/app/graph_runner.py::_try_query_via_daemon
src/frob/app/graph_runner.py::_try_affects_via_daemon
src/frob/app/graph_runner.py::_run_query
src/frob/app/graph_runner.py::_run_why
src/frob/app/graph_runner.py::_run_affects
src/frob/app/test_runner.py::run
src/frob/app/test_runner.py::_run_selected_and_report

Audit method: verified EVERY one of the 26 non-check --json runners by
REAL EXECUTION against this repo (`uv run frob <cmd> --json`, capturing
stdout/stderr to files and validating stdout as JSON), not by reading
code shape alone -- this matters because the user is about to promote
WARN gates to ERROR for a v1.0.0 release and "already safe" claims are
about to be frozen in. Runners exercised end-to-end: arch, bind, clean,
debt, deprecated, docs, doctor (timed out, code-reviewed instead --
already wraps its risky span in quiet_stdout_logs, see below), dup,
exports, fleet (timed out, code-reviewed -- already fully wrapped),
fmt, gitlog, graph (build/query/why/affects), map, mutate (timed out on
a real mutation run, code-reviewed -- no daemon-proxy/gitio span before
its own json emission), outline, parse, perf, profile, registry, stats,
test, ticket (excluded, held by a live sibling lease during this
ticket's own pre-work sweep), verify, vet, xref.

Result: 8 of 26 runners had a genuine, execution-confirmed instance of
the T-2486 bug class (an unguarded stdout write landing ahead of the
--json payload, corrupting it) -- bind, clean, docs, fmt, graph (query/
why/affects), map, test, vet. The other 18 were already safe: 12 already
wrap their risky span in `quiet_stdout_logs()` correctly scoped to
include any daemon-proxy attempt (debt, deprecated, doctor, exports,
fleet, gitlog, mutate, outline, perf, profile stats, xref -- exports and
stats both carry an explicit T-1006/T-1392 comment documenting the exact
same class of prior incident and fix), and 6 have no risky span at all
in their --json path (arch, dup, parse, profile's non-daemon subcommands,
registry, registry/parse/dup call straight into a pure-computation
library function with no subprocess/log-heavy dependency before their
own json emission).

Fix (structural, reused not reimplemented): `_guard_json_stdout_writes`/
`_StderrRedirectStdout` promoted verbatim from `check_runner.py` (T-2486)
into a new shared module `src/frob/app/_json_guard.py`; `check_runner.py`
now imports it instead of defining it locally (behavior unchanged, byte-
identical class/function bodies). Applied the guard at each confirmed
leak's exact risky span in bind/clean/docs/fmt/map/graph/test/vet,
matching this repo's own `exports_runner.py`/`stats_runner.py` precedent
(T-1006/T-1392) for where a daemon-proxy attempt's `query()` call must be
guarded but its own payload-emitting `_log.info` on a genuine hit must
NOT be (guarding only the `query()` call, never the whole helper, in
map_runner/graph_runner/test_runner).

Verification after fix: every confirmed-broken command re-run end-to-end
and its stdout re-validated as parseable JSON: `frob fmt --check --json`,
`frob clean --json`, `frob bind . --json`, `frob docs <path> --json`,
`frob graph query <ref> --json`, `frob map --json`, `frob vet --json`
(400s real network scan), and `frob test --json` (its own NotARepo
error path, confirmed empty stdout / all diagnostic noise on stderr).

Positive controls (new file `tests/unit/test_app_runners_json_guard_t2492.py`,
6 tests, all using T-2486's own `_real_console_handlers` fixture
imported from `tests/unit/test_app_runners_batch6.py` so the real
physical stdout write is exercised, not just a log record `caplog` would
see either way): bind/fmt/clean/docs plant a stray `print()` inside the
exact function this ticket's own execution found leaking and assert it
never reaches stdout and the payload stays parseable; map/graph exercise
the REAL `_daemon_proxy.query` "daemon disabled" log path (not a
synthetic plant) and assert the same.

Doc-touch note: every touched runner's `run` (or, for docs/vet where
only a private helper changed, no doc-linked symbol) landed an
AFFECT001 waiver pointing at T-2491 (docs/modules/app.md#runners sync),
same precedent T-2486 itself set.

Filed: none new (T-2491/T-2495 pre-existed as this series' next items).

Gates: `frob check --ticket T-2492` -- errors confined to this diff are
resolved (waivers added with reasons for AFFECT001 x6, SELFAUDIT001 x2
citing T-2495's design/frob.strata edit as the closing follow-up, FMT001
x2 for an already-canonical unwrappable frob:tests directive line,
DUP001 resolved by importing T-2486's fixture instead of duplicating
it); the pre-existing `fmt_runner.py::run`'s `cfg.fmt_path and Path(".")`
ty error and missing top-level frob:doc (COV001) both verified against
`git show main:src/frob/app/fmt_runner.py` as byte-identical pre-existing
gaps, untouched by this diff, left alone per scope.
`tests/unit/test_app_runners_json_guard_t2492.py` (6/6) plus the touched
existing suites (`test_app_runners_batch5.py::TestBindRunner`,
`test_app_runners_batch6.py::TestGraphRunner`,
`test_app_runners_batch6.py::TestJsonStdoutStructuralGuard`,
`test_app_runners_batch6.py::TestJsonSubcommandEnumeration`,
`test_cli_render_golden.py::TestMapGolden`, `test_graph_affects_runner.py`,
`test_vet.py`) all green: 470/470.

### Changed
```
 tickets/T-2492/ticket.md | 257 ++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 255 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/app/_json_guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, F811@/home/logan/projects/frob/.claude/worktrees/t-2492/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2492, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, invalid-argument-type@tests/unit/test_app_runners_json_guard_t2492.py, unresolved-attribute@src/frob/app/fmt_runner.py
