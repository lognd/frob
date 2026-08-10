---
id: T-1483
title: wire frob refactor into main CLI dispatch
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/**
- src/frob/__main__.py
- docs/commands/refactor.md
- tests/test_refactor.py
- tests/unit/test_main_entry.py
- src/frob/refactor/_cli.py
- tickets/T-1483/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/commands/refactor.md
  reason: the doc's own not-yet-wired claim (frob:until T-1483) must be updated now
    that wiring lands, and CLI-dispatch integration coverage needs test_refactor.py/test_main_entry.py
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_refactor.py
  reason: the doc's own not-yet-wired claim (frob:until T-1483) must be updated now
    that wiring lands, and CLI-dispatch integration coverage needs test_refactor.py/test_main_entry.py
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: the doc's own not-yet-wired claim (frob:until T-1483) must be updated now
    that wiring lands, and CLI-dispatch integration coverage needs test_refactor.py/test_main_entry.py
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/refactor/_cli.py
  reason: module docstring claims wiring is out of scope/not yet connected -- now
    stale, must be corrected
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1483/**
  reason: 'SCOPE001: ticket''s own per-ticket ledger file written by ordinary frob
    ticket CLI lifecycle commands, per T-1742/T-1737 precedent'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_main_entry.py::TestRefactorDispatch::test_refactor_subcommand_dispatches_to_run_refactor_command
- tests/unit/test_main_entry.py::TestRefactorDispatch::test_refactor_exit_code_propagates
designated_repro_test: null
threat: null
component: null
---
docs/commands/refactor.md documents frob.refactor._cli.add_refactor_parser
and run_refactor_command as built and ready, but T-1197's declared scope
never included src/frob/_cli_parsers/** or src/frob/__main__.py, so the
one-line _add_refactor_parser(sub) wiring call was never actually made.
Wire frob refactor into the main CLI dispatch. Found while draining
NEGEXIST001 (T-1477): the doc's own "not yet wired" claim had
no frob:until binding.

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
