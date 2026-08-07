## Done report

Changed:
- src/frob/tickets/_models.py::LEDGER_PATH (new)
- src/frob/tickets/_models.py::_split_scope_entries (new)
- src/frob/tickets/_models.py::_scope_globs (new)
- src/frob/tickets/_models.py::scope_matches (new, public)
- src/frob/tickets/_models.py::Ticket._normalize_scope (new field_validator)
- src/frob/tickets/_models.py::TicketSpec._normalize_scope (new field_validator)
- src/frob/tickets/__init__.py (export scope_matches)
- src/frob/tickets/_land.py::_in_scope (delegates to scope_matches)
- src/frob/gates/__init__.py::_scope_covers, scope_digest, _commit_exempts_file,
  _scope_gate_check_file (all delegate to scope_matches)

Root cause and fix: a raw scope entry like `"a/,b/,c/"` was fed straight into
`fnmatch.fnmatch` as one pattern -- it can never match a real path. `Ticket`
and `TicketSpec` now normalize `scope` at construction time (a
`field_validator` calling `_split_scope_entries`), splitting every entry on
commas, so this happens both for freshly created tickets and for tickets
loaded from a hand-edited ledger. Separately, a bare directory prefix like
`design/` (no glob metacharacters) previously matched nothing under fnmatch;
`_scope_globs` now expands any trailing-`/`, metacharacter-free entry to
`design/**`. `scope_matches` is the single shared matcher (also re-splits
defensively) that every scope-consulting call site in `frob.tickets` and
`frob.gates` (SCOPE001, PRE001's scope digest, the cross-ticket commit
exemption) now calls, so `tickets.md` is implicitly appended to every
ticket's scope glob set in one place instead of four independently-drifting
copies.

Evidence:
- tests/test_tickets.py::TestScopeMatching::test_comma_joined_entry_splits
- tests/test_tickets.py::TestScopeMatching::test_comma_joined_entry_matches_split_paths
- tests/test_tickets.py::TestScopeMatching::test_dir_prefix_globs_recursively
- tests/test_tickets.py::TestScopeMatching::test_ledger_always_in_scope
- tests/test_tickets.py::TestScopeMatching::test_new_ticket_normalizes_comma_joined_scope
- tests/test_gates.py::TestScopePrework::test_scope001_comma_joined_entry_splits_and_matches
- tests/test_gates.py::TestScopePrework::test_scope001_dir_prefix_globs_recursively
- tests/test_gates.py::TestScopePrework::test_scope001_ledger_implicitly_in_scope

Filed: none (all three sub-fixes fit this ticket's declared scope).

Gates: `frob check --ticket T-0241` -- 1 error (REL001: public API changed
since 0.22.0, add `scope_matches` to `frob.tickets`'s public surface; needs a
version bump to >= 0.23.0 via `frob release stamp`, out of this ticket's
scope -- `pyproject.toml` is not a declared scope glob, left for the
coordinator/release step). TEST006 (no coverage stamp) is expected per the
agent playbook -- the coordinator stamps coverage at land, not the
implementer. `uv run pytest tests/test_tickets.py tests/test_gates.py
tests/test_ticket_land.py -p no:cacheprovider -q` -- 270 passed, 0 failed (270
dots, 0 F/E in the run's output). `uv run pytest --collect-only -q` --
repo-wide collection succeeds (no `ModuleNotFoundError`), confirming natives
are built and all new node ids resolve.
