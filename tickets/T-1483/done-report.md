## Done report

Wired `frob refactor` into `frob`'s main CLI dispatch. Because
`run_refactor_command(args: argparse.Namespace) -> int` takes a parsed
`Namespace` and returns a raw exit code directly (T-1197's own shape,
built to match every other `_add_*_parser` builder's signature) rather
than the uniform `run(AppConfig)` entry point every `Subcommand`-mapped
runner in `frob.app.app._SUBCOMMAND_RUNNER_NAMES` shares, `frob
refactor` is routed through `src/frob/__main__.py::_dispatch` the same
way `bind`/`agent`/`worktree` already are: recognized as `argv[0] ==
"refactor"` and dispatched directly, before the main `argparse` parser
tree (`_build_parser`) is even built. It never becomes a `Subcommand`
enum member or an `app.py` dict entry, so no file outside this ticket's
declared scope needed to change for the dispatch mechanism itself.

Updated `docs/commands/refactor.md`'s "CLI wiring status" section and
top banner (removed the stale `frob:until T-1483`/"not yet wired"
claim) and `src/frob/refactor/_cli.py`'s module docstring (both
described the wiring as future/out-of-scope, now stale).

Scope was declared as `src/frob/_cli_parsers/**` + `src/frob/__main__.py`
only; extended (reasons recorded in the scope_changes audit trail) to
`docs/commands/refactor.md` and `src/frob/refactor/_cli.py` (stale
"not yet wired" claims), `tests/test_refactor.py` (pre-work sweep
closure), `tests/unit/test_main_entry.py` (new dispatch-routing test
coverage), and `tickets/T-1483/**` (SCOPE001, the ticket's own
per-ticket ledger file).

New tests in `tests/unit/test_main_entry.py::TestRefactorDispatch`:
one confirms `_dispatch(["refactor", "rename", ...])` builds the
correct `Namespace` (source/destination `SymbolRef`s) and calls
`run_refactor_command`, exiting with its return code; the other
confirms a non-zero return code propagates as the process exit code.
All 65 pre-existing tests in `tests/test_refactor.py` and 15 in
`tests/unit/test_main_entry.py` continue to pass unmodified.

### Changed
```
 docs/commands/refactor.md     | 29 +++++++++++++++--------------
 src/frob/__main__.py          | 24 ++++++++++++++++++++++++
 src/frob/refactor/_cli.py     | 16 ++++++++--------
 tests/unit/test_main_entry.py | 40 +++++++++++++++++++++++++++++++++++++++-
 tickets/T-1483/ticket.md      | 41 ++++++++++++++++++++++++++++++++++++++++-
 5 files changed, 126 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestRefactorDispatch::test_refactor_subcommand_dispatches_to_run_refactor_command` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestRefactorDispatch::test_refactor_exit_code_propagates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 3 error(s), 739 warning(s), 732 waived
- error-findings: ARCH001@src/frob/tickets/_new_renumber.py, invalid-assignment@tests/test_ticket_land.py, invalid-return-type@src/frob/tickets/_new_renumber.py
