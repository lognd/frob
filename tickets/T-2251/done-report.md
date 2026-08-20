## Done report

Built `frob format [path] [--select-imports-only]`, the frob-native
replacement for the Makefile's `format`/`lint-fix`/`all` targets
(T-1382 epic). Found `frob.check._python._run_ruff_autofix` already
built by T-2320/T-2252 (exposed as `frob check --fix-ruff`) -- reused
it directly for the default full-rule-set path instead of duplicating
its subprocess plumbing; added only the `--select-imports-only`
(`ruff check --fix --select I`) narrower path plus a small reused
`ruff format` write helper.

Wired `Subcommand.format` through `app.py` (`_RUNNER_MODULE_NAMES`,
`_SUBCOMMAND_RUNNER_NAMES`, `_import_runner_module`, usage string),
`config.py` (`Subcommand.format`, `format_path`/
`format_select_imports_only` fields), `_config_external.py`
(`_STRING_FIELDS`/`_BOOL_FLAGS`), `_cli_parsers/_misc.py` +
`__init__.py` (`_add_format_parser`), `__main__.py`.

Docs: `docs/commands/format.md` (new), `docs/modules/app.md#runners`,
`docs/modules/cli.md` regenerated via `frob docs --sync-commands`,
`README.md` command table + count bump to 46.

Tests: `tests/unit/test_pyfmt_runner.py`, 5 cases -- default delegates
to `_run_ruff_autofix`, `--select-imports-only` issues the narrower
ruff invocation, nonzero exit propagates, plus a tool-unavailable case
each for the two new helpers. All evidence-bound.

Verified end-to-end on scratch input outside the test suite: both the
default and `--select-imports-only` paths correctly rewrite real
broken code (import sort, spacing, ruff-format).

Gates: `frob check --ticket T-2251 --only ruff --only ty` and
`frob check --ticket T-2251 --only gates` both clean of any finding in
this ticket's own files (DOC005/DOC012/PRE001 fixed during the ticket;
remaining errors are pre-existing repo-wide baggage -- import-cycle
warning, I001 backlog, etc. -- unrelated to this change).

### Changed
```
 Makefile                             |  40 ++++++++---
 README.md                            |   3 +-
 docs/commands/format.md              |  39 ++++++++++
 docs/modules/app.md                  |   7 ++
 docs/modules/cli.md                  |   1 +
 src/frob/__main__.py                 |   2 +
 src/frob/_cli_parsers/__init__.py    |   2 +
 src/frob/_cli_parsers/_misc.py       |  27 +++++++
 src/frob/app/_config_external.py     |   4 ++
 src/frob/app/app.py                  |   6 +-
 src/frob/app/config.py               |  15 ++++
 src/frob/app/pyfmt_runner.py         | 136 +++++++++++++++++++++++++++++++++++
 tests/unit/test_makefile_coverage.py |  82 +++++++++++++++++++++
 tests/unit/test_pyfmt_runner.py      | 131 +++++++++++++++++++++++++++++++++
 tickets/T-2244/ticket.md             |  23 +++++-
 tickets/T-2251/ticket.md             |   6 ++
 16 files changed, 509 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/test_pyfmt_runner.py::TestRun::test_default_delegates_to_run_ruff_autofix` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRun::test_select_imports_only_uses_dash_dash_select_i` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRun::test_nonzero_exit_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRunRuffCheckFixSelectImports::test_missing_binary_yields_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRuffFormatWriteOnly::test_missing_binary_yields_typed_result` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 33 error(s), 896 warning(s), 707 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
