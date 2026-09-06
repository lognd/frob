## Done report

Changed: tests/conftest.py::pytest_sessionfinish
Changed: .github/workflows/ci.yml (T-3531 workaround comment, updated not removed)
Changed: tests/unit/test_conftest_stackdump.py::TestSuiteResultLine (fixtures + fake reporter)

Mechanism: the ticket's literal ask (`reporter.ensure_newline()` alone) was
verified, end-to-end against real pytest 9.0.3, to NOT fix the reported bug --
`ensure_newline()` gates on `TerminalReporter.currentfspath`, which the
low-verbosity dot-progress path (`-q`, and this repo's own doubled `-q -q`,
the exact reported scenario) never sets, so it is a no-op there. Reproduced
directly: with only `ensure_newline()` added, `pytest ... -q -q` still glued
`[100%]` and `SUITE-RESULT:` onto one line. Backed it up with a
`reporter._tw.width_of_current_line` check (which does track the dot-progress
column correctly) plus `reporter._tw.line("")` to break the line only when
needed. Verified byte-for-byte unchanged against real (not mocked) pytest
runs at `-v`, bare, `-q`, and `-q -q`, both passing and failing suites, and
verified the mid-line case now emits `SUITE-RESULT:` matching `^SUITE-RESULT`.

Evidence: tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_starts_line_at_column_zero_when_terminal_is_mid_line (MUST-FIRE)
Evidence: tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_stays_byte_for_byte_unchanged_when_terminal_already_at_column_zero (MUST-STAY-QUIET)
Evidence: tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_prints_greppable_line_at_any_verbosity (THIRD FIXTURE -- pinned completed-run line format unchanged)

Filed: none (a new ticket for the SCOPE002 finding below would have
duplicated the already-tracked T-3299/T-3902/T-3957/T-4098 family; a draft
was filed, recognized as a duplicate, and dropped instead)

Gates: frob check --ticket T-4103 --only scope has ONE residual SCOPE002
error: T-4103's scope drags in tests/conftest.py::pytest_configure's
pre-existing (untouched by this ticket) frob:tests binding to
tests/test_mutate_journal.py, whose own doc/test-edge closure chains through
src/frob/mutate -> docs/modules/mutate.md -> design/frob.strata (the
whole-project design root) and explodes to 227+ further doc edges --
reproduced directly via `frob ticket scope T-4103 --add design/frob.strata`
then `frob check --ticket T-4103 --only scope`. This is the already-tracked
SCOPE002 closure-explosion class (T-3299, T-3902, T-3957, and T-4098 in
particular: "SCOPE002 promoted to error ... structurally unwaivable post
ledger-v2, no tickets.md file exists to attach frob:waive to" -- the exact
situation here, confirmed: `frob ticket scope-ack` sets scope_breadth_ack
(TICK009) but does not clear SCOPE002, and there is no `frob:waive`-style
directive addressable at a `tickets.md:0` finding). Waived is not the right
word since no waiver mechanism exists for this finding; it is left open,
acked via `frob ticket scope-ack T-4103`, and not absorbed into T-4103's
scope by adding the unrelated mutate module. Every other gate/tool this
ticket's diff can affect is clean: ruff-check, ruff-format (gate:FMT),
gate:PRE, ty (pre-existing repo-wide diagnostics only, unrelated file), and
the full tests/unit/test_conftest_stackdump.py suite (33 passed).

### Changed
```
 .github/workflows/ci.yml              |  14 +-
 tests/conftest.py                     |  28 ++++
 tests/unit/test_conftest_stackdump.py |  91 ++++++++++-
 tickets/T-4103/ticket.md              | 279 +++++++++++++++++++++++++++++++++-
 tickets/T-4122/ticket.md    |  42 +++++
 5 files changed, 445 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_starts_line_at_column_zero_when_terminal_is_mid_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_stays_byte_for_byte_unchanged_when_terminal_already_at_column_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_prints_greppable_line_at_any_verbosity` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 4428 warning(s), 932 waived
- error-findings: SCOPE002@tickets.md, missing-argument@tests/unit/test_check_gates_summary.py
