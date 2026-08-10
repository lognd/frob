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
