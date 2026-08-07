## Done report

User-requested UX fix (2026-07-22): frob ticket subcommands printed the full
gitio/tickets DEBUG-INFO diagnostic firehose because the stdout handler
defaults to DEBUG and only frob check applied T-0202 quieting; the ticket
CLI's own output is its module logger's INFO, so a handler-level clamp
would have swallowed the listing itself. Added frob.logging.logger_levels
(per-logger save/restore context manager), dispatched every ticket
subcommand under a clamp (frob tree -> WARNING, runner logger pinned INFO),
and added frob ticket -v to restore the firehose. WARNING+ diagnostics
(stale leases, over-broad scopes) still show by default. REL001 minor bump
to 0.97.0 for the new public API.

### Changed
```
 .frob-release.json                |  3 +-
 pyproject.toml                    |  2 +-
 src/frob/__main__.py              | 11 +++++
 src/frob/app/config.py            |  4 ++
 src/frob/app/ticket_runner.py     | 25 +++++++++-
 src/frob/logging/__init__.py      |  3 +-
 src/frob/logging/quiet.py         | 25 ++++++++++
 tests/test_ticket_runner_quiet.py | 41 +++++++++++++++++
 tests/unit/test_logging_quiet.py  | 50 ++++++++++++++++++++
 tickets.md                        | 97 +++++++++++++++++++++++++++++++++++++++
 uv.lock                           |  2 +-
 11 files changed, 257 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_default_clamps_frob_tree_but_pins_runner_output` (pytest node id, verified passing when recorded)
- `tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_verbose_skips_the_clamp` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_quiet.py::TestLoggerLevels::test_sets_and_restores_mapped_levels` (pytest node id, verified passing when recorded)
