## Done report

The producer half of T-2521. A parser that returns exit_code=1 with an
empty diagnostic list is, to every caller that reads only `diagnostics`,
byte-identical to a clean run -- the shape that auto-dropped seven sweep
tickets and ~66 finding identities. T-2521 guarded two consumers; this
makes the parsers themselves stop lying, so the third consumer does not
rediscover the bug.

MEASURED PER-PARSER INVENTORY (every module in
src/frob/process/parsers/), before this change:

Silent on failure (FIXED here):
- ruff.parse_ruff_json     -- JSONDecodeError -> exit 1, diagnostics=[]
- eslint.parse_eslint      -- JSONDecodeError -> exit_code or 1, []
- junit.parse_junit_xml    -- ET.ParseError   -> exit 1, []
- valgrind._parse_xml      -- ET.ParseError   -> caller's exit code
                              (possibly ZERO) with [] -- worst of the set
- cargo._cargo_json_diagnostic -- swallowed a malformed JSON line and
                              returned None, indistinguishable from a
                              deliberately filtered non-compiler-message

Already loud, unchanged:
- common.tool_unavailable_result / tool_disabled_result /
  tool_crash_result -- each already attaches an error Diagnostic (the
  posture this ticket generalizes)

No parse-failure branch at all (regex/line scanners that cannot fail to
decode; nothing to fix):
- ruff.parse_ruff_text, ruff.parse_ruff (dispatcher), tsc.parse_tsc,
  clang.parse_clang, clang_tidy.parse_clang_tidy, ty.parse_ty,
  pytest.parse_pytest, valgrind._parse_text, cargo._parse_cargo_text

FIX: new shared helper `tool_parse_failure_result` in
parsers/common.py, mirroring tool_crash_result/tool_disabled_result:
failing exit code (never zero-able -- exit_code=0 is coerced to 1) plus
one error Diagnostic naming what failed. ruff/eslint/junit/valgrind route
their fallbacks through it; cargo appends an equivalent error Diagnostic
for each undecodable line while still filtering well-formed
non-compiler-message lines silently, as before.

POSITIVE CONTROLS, BOTH DIRECTIONS (tests/unit/
test_parser_failure_diagnostics.py, 24 tests, all passing):
- TestUnparsableOutputIsLoud: each of the five failure paths now yields
  non-empty, error-severity diagnostics and a nonzero exit code.
- TestCleanRunsAreUnchanged: clean ruff/eslint/junit/valgrind/cargo runs
  still produce zero diagnostics and exit 0; eslint's empty-output path
  is unchanged; a well-formed cargo compiler-artifact line is still not
  a finding.
- test_warning_only_nonzero_exit_is_not_a_crash: a warning-only nonzero
  ruff exit keeps its real warning diagnostics, is not rewritten as a
  parse failure, and is not flagged by T-2521's consumer guard.
- test_consumer_guard_no_longer_sees_a_silent_failure: _incomplete_tool_
  results returns [] for the fixed ruff payload -- the guard STAYS, it
  simply has nothing to catch here now (defence in depth, unweakened; no
  line of _verify.py was touched).

Repro discipline: the fix and the test were committed separately so the
repro is genuinely observable. `frob ticket evidence --designate-repro
... --base-ref 314b5077a` reported FAILED_AT_PARENT.

MEASUREMENT: `frob check --land-parity` -- 47 unscoped errors with my
findings present, 38 after, and zero of the remaining 38 touch
src/frob/process/parsers/** or my test files. Scoped `--only affect_drift
--ticket T-2537`: gate:AFFECT 0 errors, 4 waived. Targeted pytest:
exitstatus=0 collected=73 failed=0.

DISCLOSED CUT: docs/modules/process.md could NOT be updated -- it is held
by T-2374's live cross-worktree lease and `frob ticket scope --add`
refused with ScopeLeaseConflict. The drafted doc text was reverted and
four AFFECT001 waivers (one per touched parser) stand in its place, each
naming the lease. Residue ticket filed to add the doc section and remove
those waivers once T-2374 lands.

CONTRADICTING THE PREMISE: nothing. The premise held exactly; the ticket
undercounted the blast radius -- five parse-failure paths were silent,
not two, and valgrind's was worse than ruff's because it propagated the
caller's exit code, so an unparsable memcheck report could read as a
PASSING clean run.

### Changed
```
 src/frob/process/parsers/cargo.py             |  25 +++++
 src/frob/process/parsers/common.py            |  39 ++++++++
 src/frob/process/parsers/eslint.py            |  17 +++-
 src/frob/process/parsers/junit.py             |  17 +++-
 src/frob/process/parsers/ruff.py              |  20 +++-
 src/frob/process/parsers/valgrind.py          |  17 +++-
 tests/unit/test_parser_failure_diagnostics.py | 128 ++++++++++++++++++++++++++
 tests/unit/test_ts_parsers.py                 |   5 +-
 tickets/T-2537/ticket.md                      |  28 +++++-
 tickets/T-2544/ticket.md            |  50 ++++++++++
 10 files changed, 327 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/unit/test_parser_failure_diagnostics.py::TestUnparsableOutputIsLoud::test_ruff_malformed_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_parser_failure_diagnostics.py::TestUnparsableOutputIsLoud::test_eslint_malformed_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_parser_failure_diagnostics.py::TestUnparsableOutputIsLoud::test_junit_malformed_xml` (pytest node id, verified passing when recorded)
- `tests/unit/test_parser_failure_diagnostics.py::TestUnparsableOutputIsLoud::test_valgrind_malformed_xml` (pytest node id, verified passing when recorded)
- `tests/unit/test_parser_failure_diagnostics.py::TestUnparsableOutputIsLoud::test_cargo_malformed_json_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_parser_failure_diagnostics.py::TestCleanRunsAreUnchanged::test_ruff_clean_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_parser_failure_diagnostics.py::TestCleanRunsAreUnchanged::test_warning_only_nonzero_exit_is_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_parser_failure_diagnostics.py::TestParseFailureResult::test_attaches_error_diagnostic` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2537/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2537/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2537/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2537/src/frob/testing/_collect_kotlin.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2537/tests/unit/test_ticket_runner_repro_merge_base.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2537, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
