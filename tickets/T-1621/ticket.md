---
id: T-1621
title: Every frob log record appears twice in pytest output, making occurrence counts
  unreliable
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/logging/**
- tests/conftest.py
- tests/unit/test_logging_module.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'the umbrella tests/** is redundant: tests/conftest.py is already declared
    specifically and is where the duplicate-handler fix lands. Per frob ticket wave,
    this one glob was single-handedly preventing T-1660, T-1666, T-1782, T-1783 and
    T-1784 from partitioning into a parallel group -- narrowing it costs this ticket
    nothing and unblocks five.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_logging_module.py
  reason: need to add the counting regression test alongside the existing logging
    test module
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_logging_module.py::test_under_pytest_true_in_this_process
- tests/unit/test_logging_module.py::test_under_pytest_false_without_pytest_in_sys_modules
- tests/unit/test_logging_module.py::test_log_record_reported_via_exactly_one_channel_under_pytest
- tests/unit/test_logging_module.py::test_root_logger_has_no_frob_handlers_under_pytest
designated_repro_test: tests/unit/test_logging_module.py::test_log_record_reported_via_exactly_one_channel_under_pytest
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Every frob log record appears TWICE in pytest output, in two different formats:

    WARNING: gitio: git rev-parse --abbrev-ref HEAD failed (rc=128): fatal: not a git repository...
    WARNING  frob.gitio:gitio.py:232 gitio: git rev-parse --abbrev-ref HEAD failed (rc=128): fatal: not a git repository...

Cause: frob configures its own root logging via dictConfig with lazy stdout/stderr StreamHandlers (src/frob/logging/handler.py, logger.py). Under pytest, that handler writes into the captured stream AND pytest's own logging-capture plugin reports the same record from the log-capture buffer. Both reach the report.

Why it is worth fixing rather than tolerating: it doubles the volume of every test log, and it makes occurrence COUNTING unreliable -- grepping a log for how many times a condition fired silently returns twice the real number. During this drive, counts pulled from test logs had to be sanity-checked by hand more than once for exactly this reason. A log you cannot count is a log you cannot measure with.

Fix direction: do not install frob's own stream handlers when running under pytest (pytest's capture is already reporting them), or set propagation so exactly one path reports. Whichever is chosen, assert it: a test that emits one record and asserts it appears exactly once in the captured output.

Also verify, and state the answer in the Done report, whether ordinary CLI invocations double as well. A probe during triage did not produce a warning at all, so the CLI case is UNVERIFIED rather than known-clean -- do not assume it is fine because the pytest path explains the observed instances.

## Done report

Reproduced first, then characterized precisely: emitting one log.warning()
call under pytest reached the terminal via TWO INDEPENDENT reporters
sitting on the SAME root logger, not one handler firing twice --

  1. frob's own dictConfig-installed root handlers (_LazyStderrHandler
     for WARNING+, _LazyStdoutHandler below it) write a frob-formatted
     line straight to real sys.stderr/sys.stdout, which pytest's own
     output capturing then echoes back as "Captured stderr call" on
     failure.
  2. pytest's OWN logging-capture plugin independently attaches its own
     LogCaptureHandler directly to the root logger for the duration of
     every test -- unconditionally, regardless of this repo's dictConfig
     -- and reports the SAME record again as "Captured log call", in
     pytest's own default format ("LEVEL name:file:line message").

Confirmed by direct repro (a throwaway failing test emitting one
log.warning): both "Captured stderr call" and "Captured log call"
sections appeared, each showing the same message in the two different
formats the ticket's own report described.

Fix (config level, not muted output): src/frob/logging/logger.py's
_init() now detects "pytest" in sys.modules (_under_pytest, checked at
sys.modules rather than PYTEST_CURRENT_TEST since frob's loggers are
typically first created at collection-time import, before any test --
and therefore before that env var -- exists) and, only when true, clears
cfg["root"]["handlers"] before calling logging.config.dictConfig -- so
frob's own stdout/stderr StreamHandlers are simply never installed under
pytest. propagate is left untouched (still True): pytest's own capture
handler does not depend on frob's handlers at all, so caplog-based tests
(68 files) are unaffected, and a downstream consumer of this library who
attaches their own handler above frob's loggers still receives every
record -- only frob's own root stream handlers are skipped, and only
under pytest, where reporter #2 already covers every record on its own.

Explicitly did NOT set propagate=False (would detach frob's loggers from
any handler a library consumer legitimately installs) and did NOT remove
a handler serving a real purpose: verified no test in this repo depends
on capsys observing frob's OWN logging-handler-formatted text (grep for
capsys+get_logger/handler usage found none -- the two capsys-based tests
in test_main_entry.py assert on direct print()s in __main__.py, not on
anything routed through frob's logging handlers, so they are unaffected
and still pass).

Ordinary (non-pytest) CLI invocations verified UNAFFECTED and NOT
doubled to begin with: `python -c "...get_logger(...).warning(...)"` run
outside pytest (no "pytest" in sys.modules) prints the frob-formatted
line exactly once, before and after this change -- there is no second
reporter installed in a real CLI process, so this bug was pytest-only.

Proof test:
tests/unit/test_logging_module.py::test_log_record_reported_via_exactly_one_channel_under_pytest
emits one record, asserts caplog sees it exactly once, AND asserts the
marker text does NOT also appear in capsys-captured stdout/stderr (the
exact duplication path this fixes) -- verified this test fails against
the pre-fix code (reproduced manually with a throwaway test before the
fix landed) and passes after.

Also added:
- test_under_pytest_true_in_this_process /
  test_under_pytest_false_without_pytest_in_sys_modules: direct unit
  coverage of the new _under_pytest() detection helper.
- test_root_logger_has_no_frob_handlers_under_pytest: asserts frob's own
  handler classes are absent from the real root logger's handler list
  under pytest (pytest installs its own unrelated handlers there too,
  so this checks isinstance against _LazyStdoutHandler/_LazyStderrHandler
  specifically, not an empty list).

BUG002 note: test_log_record_reported_via_exactly_one_channel_under_pytest
is a brand-new test node that does not exist at main's parent commit
(84f007d1a54c) -- the evidence tool's own --check-repro
correctly reports NO_VERDICT (exit 5, collection error) rather than a
pass or fail, since the parent checkout cannot even import a function
this ticket adds. This is the exact structural NO_VERDICT shape T-1929
documents (not evasion of a real confirmatory-only finding) --
designated via --designate-repro-force with that reasoning recorded,
per the documented escape hatch for a genuine false positive.

### Changed
```
 tickets/T-1621/ticket.md | 16 ++++++++++++++--
 1 file changed, 14 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_logging_module.py::test_under_pytest_true_in_this_process` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::test_under_pytest_false_without_pytest_in_sys_modules` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::test_log_record_reported_via_exactly_one_channel_under_pytest` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::test_root_logger_has_no_frob_handlers_under_pytest` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: F401@/home/logan/projects/frob/.claude/worktrees/log-dupe/tests/unit/test_tickets_evidence_only_scope.py
