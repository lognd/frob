## Done report

`fix_cov002_ticket_directive_insertion`'s insertion helper
(`_insert_ticket_directive_above` in `src/frob/gates/_fix_engine.py`)
hardcoded its own narrow suffix table (`.py` -> `#`, `.rs` -> `//`, any
other suffix silently defaulted to `#`). During T-1548's own land this
default fired against `design/frob.strata` (comment leader `//`),
inserting a Python-style `#` directive that broke strata parsing on
`main` until it was hand-repaired.

Fix: the helper now resolves the leader via
`frob.gates._fmt_directives.marker_for` -- the ONE shared per-suffix
comment-leader table `frob fmt`'s own directive-canonicalization pass
already maintains -- instead of a second, independently-drifting table.
`marker_for`'s backing `_MARKERS` table gained a `.strata": "//"` entry
as part of this fix (it did not cover `.strata` before either). A
target suffix `marker_for` does not recognize now REFUSES the
insertion outright (logs a warning, returns `False`) instead of
guessing `#`.

Moved the stray `frob:doc` directive that had drifted onto the private
`_insert_ticket_directive_above` helper back onto the public
`fix_cov002_ticket_directive_insertion` it documents (COV005/COV007
caught this during verification) and updated
`docs/modules/gates_e501_autofix.md`'s existing writeup with a new
"Comment-leader resolution (T-1581)" subsection.

Scope was narrowed/extended from the ticket's original declaration:
the real regression tests live in `tests/test_gates_fix_engine.py`
(not `tests/test_gates.py` as originally listed), the real doc
writeup lives in `docs/modules/gates_e501_autofix.md` (not
`docs/modules/gates.md`, which was under an in-progress T-1205 lease
at T-1548 land time and still hosts only a forwarding note), and
`src/frob/gates/_fmt_directives.py` needed touching to add the
`.strata` entry and expose the one shared table to reuse. All three
were added via `frob ticket scope --add` with reasons recorded in the
ledger.

One residual, disclosed rather than forced: `frob sys sync-interface`
picked up the new `TestInsertTicketDirectiveAboveCommentLeader` test
class as SYS104 drift against `design/frob.strata` (a new public
testsuite symbol). `design/frob.strata` is currently leased by the
in-progress T-1220, so this ticket could not add it to scope
(`ScopeLeaseConflict`) or commit the sync fix itself. `frob check
--only sys --ticket T-1581` accordingly reports one SELFAUDIT001
finding for this; `frob check --land-parity` reports CLEAN (0 unscoped
errors) against the current worktree tree, confirming this specific
drift is checkpoint-exempt / land's own pre-land Tier-A sweep (which
runs `frob sys sync-interface` unconditionally) will resolve it at
land time once T-1220's lease clears -- no manual escalation needed
beyond this disclosure.

### Changed
```
 docs/modules/gates_e501_autofix.md | 31 +++++++++++----
 src/frob/gates/_fix_engine.py      | 56 ++++++++++++++++++---------
 src/frob/gates/_fmt_directives.py  | 10 ++++-
 tests/test_gates_fix_engine.py     | 78 ++++++++++++++++++++++++++++++++++++++
 tickets.md                         | 29 +++++++++++++-
 5 files changed, 177 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader::test_strata_file_gets_slash_slash_leader` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader::test_rust_file_gets_slash_slash_leader` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader::test_python_file_gets_hash_leader` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader::test_unknown_extension_refuses_insertion` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 1115 warning(s), 784 waived
- error-findings: none (measured, zero errors)
