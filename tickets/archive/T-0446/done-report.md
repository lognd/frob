## Done report

T-0323 (adding the `frob ticket merge-driver` subcommand) had to run `frob
ticket scope --add` three separate times just to touch
`src/frob/__main__.py`, `src/frob/app/config.py`, and
`src/frob/app/ticket_runner.py` -- the same three files EVERY feature
ticket that adds a new subcommand structurally needs, regardless of what
scope was declared when the ticket was filed. This ticket closes that
recurring "scope-expansion ceremony" gap.

Fix: `frob.tickets._models.CLI_WIRING_FILES` names the three well-known
wiring files. `scope_matches` gains an optional `kind: TicketKind | None =
None` keyword: when `kind is TicketKind.FEATURE`, these files are ALSO
treated as implicitly in scope, mirroring the exact pattern T-0241
established for `tickets.md` (`LEDGER_PATH`, always in scope for every
ticket regardless of kind). `scope_gate` (the SCOPE001 gate implementation
in src/frob/gates/__init__.py) now passes `ticket.kind` through to
`scope_matches`, so a feature ticket's edits to these files no longer trip
SCOPE001. `kind=None` (the default, and every pre-T-0446 call site)
preserves prior behavior exactly -- this is additive, never a loosening of
an existing check: non-FEATURE tickets (bug/docs/security/...) still trip
SCOPE001 on these files exactly as before, since an unannounced edit to
the CLI dispatch table from a bug ticket is real scope creep, not the
structural necessity this closes.

docs/modules/tickets.md's "Scope/lease change protocol" section now
documents the new implicit-scope rule directly under its existing T-0446
example (which previously only showed the manual `frob ticket scope --add`
workaround).

REL001: `scope_matches`'s signature changed and a new public
`CLI_WIRING_FILES` constant was added -- version bumped 0.50.0 -> 0.51.0,
CHANGELOG.md entry added, uv.lock refreshed, `frob release stamp` run.

Regression tests: both at the `scope_matches` unit level (feature vs.
non-feature kind) and at the `scope_gate` (SCOPE001) integration level
(a feature ticket's diff touching all three wiring files passes cleanly;
a bug ticket's diff touching the same file still fires SCOPE001).

### Changed
```
 .frob-release.json                 |   5 +-
 CHANGELOG.md                       |  15 ++++
 docs/modules/tickets.md            |  37 +++++++--
 pyproject.toml                     |   2 +-
 src/frob/app/ticket_runner.py      |  25 +++++-
 src/frob/gates/__init__.py         |   7 +-
 src/frob/tickets/_models.py        | 101 +++++++++++++++++++-----
 src/frob/tickets/_store.py         |  98 ++++++++++++++++++-----
 tests/test_gates.py                |  33 +++++++-
 tests/test_tickets.py              |  50 ++++++++++++
 tests/test_tickets_evidence_cli.py |  43 +++++++++++
 tests/unit/test_ticket_store.py    |  14 ++++
 tickets.md                         | 154 +++++++++++++++++++++++++++++++++++--
 uv.lock                            |   2 +-
 14 files changed, 524 insertions(+), 62 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestScopeMatching::test_feature_kind_implies_cli_wiring_files_in_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeMatching::test_non_feature_kind_does_not_imply_cli_wiring_files` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_scope001_feature_ticket_cli_wiring_files_implicitly_in_scope` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_scope001_non_feature_ticket_cli_wiring_files_still_out_of_scope` (pytest node id, verified passing when recorded)
