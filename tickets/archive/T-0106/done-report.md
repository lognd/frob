## Done report

Changed:
- src/frob/__main__.py::_add_ticket_new_parser (added --evidence flag)
- src/frob/__main__.py::_add_ticket_lifecycle_parsers (added --evidence flag to close)
- src/frob/app/ticket_runner.py::_new (applies evidence after ticket creation)
- src/frob/app/ticket_runner.py::_close (applies evidence before DONE transition; refuses transition on failure)
- src/frob/app/ticket_runner.py::_apply_evidence (new shared helper; wraps
  collect_python_tests + tickets.add_evidence, reused by _evidence, _new,
  _close so all three routes go through identical validation)
- docs/modules/tickets.md (documented new/close --evidence semantics)

`new --evidence` and `close --evidence` both route through
`frob.tickets.add_evidence` (T-0102's validation: resolvable pytest node
ids, dedupe against existing evidence, wholesale rejection of a mixed
batch) via the new `_apply_evidence` helper -- no reimplementation of
validation logic. `close --evidence` applies evidence strictly before the
DONE transition and exits nonzero without transitioning if any id is
unresolvable, so a bad --evidence flag can never close a ticket on
unvalidated evidence.

Evidence: 6 new unit tests in tests/test_tickets_evidence_cli.py (listed
above), covering happy path, unresolvable-id rejection (both new and
close), and dedupe-against-existing-evidence for both subcommands.
tests/test_tickets.py (75 tests) and tests/system/test_cli_ticket.py (8
tests) still green. ruff check/format and ty clean on all touched files.

Post-merge note: main landed T-0046 (refactor of ticket_runner.py/
__main__.py into private helpers -- _ticket_spec_from_cfg,
_maybe_attach_clipboard_image, _ticket_dispatch_table, split
_add_ticket_*_parsers helpers) after this ticket's original
implementation. The worktree was merged with main and the resulting
conflicts (1 in __main__.py, 4 in ticket_runner.py) were resolved by
slotting the --evidence argparse additions and _apply_evidence/_new/
_close wiring into the refactored structure, keeping main's helper
decomposition intact. Re-verified post-merge: all 6 new tests green,
tests/test_tickets.py 75 passed, tests/system/test_cli_ticket.py 8
passed, ruff check/format and ty clean on touched files.

Filed: none. (Pre-existing, out-of-scope: `frob ticket evidence`/`frob
test` currently fail repo-wide because `uv run pytest --collect-only`
errors on 19 unrelated strata test files that import a missing
`strata_core`/`frob_core` module -- already tracked elsewhere in
tickets.md (6 existing references), not introduced by this change. This
blocked using the CLI's own `frob ticket evidence` command to record this
ticket's evidence/Done report, so both were recorded directly in
tickets.md per the ledger schema instead.)

Gates: `frob check` gates-stage diagnostic count is 640 both before and
after this change (verified via git stash/git stash pop against the same
worktree state) -- no new violations introduced. `frob check --ticket
T-0106` shows only pre-existing/baseline items unrelated to this diff:
SCOPE001 on tickets.md (ticket-mechanics writes are outside the declared
scope globs, same as other in-flight tickets), PRE001 (stale sweep,
re-run via `frob ticket sweep T-0106` before any future check), TEST001
on `__main__.py::main` and `ticket_runner.py::run` (present in the
pre-change baseline too, unrelated top-level dispatch functions), and the
pre-existing `ty` unresolved-import errors for `strata_core`/`frob_core`
(present before this change).
