## Done report

Changed:
- src/frob/app/deprecated_runner.py (new): `run(cfg)` -- `frob deprecated` entry point, mirrors `frob.app.debt_runner`'s shape (snapshot load, `--json`/human dual mode, no mutation); also loads the ticket queue (`frob.tickets.load_queue`) and computes an `in-window`/`past-sunset`/`orphaned` status per entry via `_status_of`/`_load_ticket_states`.
- src/frob/app/config.py: `Subcommand.deprecated`, `AppConfig.deprecated_path`/`deprecated_json` fields, wired into the existing path/bool field-collection lists.
- src/frob/__main__.py: `_add_deprecated_parser` (`--path`/`--json`), registered in `_add_workflow_subparsers`.
- src/frob/app/app.py: `deprecated_runner` added to `_RUNNER_MODULE_NAMES` and `_SUBCOMMAND_RUNNER_NAMES`, usage string updated.
- README.md: new `frob deprecated` command-table row; total-command count bumped 34 -> 35 (DOC005).
- docs/modules/gates.md: DEPRECATED gate section now documents the CLI and its tri-state status classification.
- tests/test_deprecated_runner.py (new): `TestDeprecatedRunner` -- JSON mode, clean-repo message, past-sunset status, orphaned status (closed-ticket) cases.

Evidence:
- tests/test_deprecated_runner.py::TestDeprecatedRunner::test_json_mode_lists_deprecated_entries
- tests/test_deprecated_runner.py::TestDeprecatedRunner::test_no_deprecations_logs_clean_message
- tests/test_deprecated_runner.py::TestDeprecatedRunner::test_human_mode_reports_past_sunset_status
- tests/test_deprecated_runner.py::TestDeprecatedRunner::test_human_mode_reports_orphaned_status_for_closed_ticket

Filed: none

Gates: `frob check --ticket T-0638` clean across all five chunked stages (gates-fast, gates-native, gates-security, lint, static) -- 0 errors in each after two fix rounds (COV002 missing `frob:ticket` directives on the new test file, DRIFT002 test-symref separator typo, INV006 exclusivity wording in new docstrings, FMT001 long directive line, ruff-format). `frob test --base main` (touched-set) passed 5/5 selected node ids, exit 0.
