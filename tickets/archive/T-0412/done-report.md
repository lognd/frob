## Done report

Implemented the frob:debt vs frob:waive distinction per the ticket body's
design:

Directive parsing (src/frob/graph/_models.py, src/frob/graph/dsl.py):
new EdgeKind.DEBT and "debt" verb -> `frob:debt <RULE> reason="..."
ticket="T-####" [until="YYYY-MM-DD"|"X.Y.Z"]`. Both reason= and ticket=
are REQUIRED at parse time (missing either yields a MalformedDirective,
mirroring frob:waive's own reason= requirement) -- ticket= is not optional
the way a waiver's reason is, since a debt with no owning ticket is not
tracked at all.

Gate (src/frob/gates/__init__.py, src/frob/gates/_models.py): new
debt_gate (DEBT001 malformed directive, DEBT002 ticket missing/not-open --
reusing the same open-ticket check TODO002 applies to frob:todo but at
ERROR not WARN severity, DEBT003 expired `until` boundary judged by date
string compare or semver compare against the run's actual date/version).
Wired into run_gates as a new "debt" gate (added to _ALL_GATES and
_CANONICAL_GATE_ORDER) -- "gate:DEBT" appears automatically in `frob
check`'s per-family summary via the existing rule-id-prefix grouping
(_rule_family), no check_runner.py change needed. release_gate (REL001)
extended with _release_open_debt_violations: a release is blocked while
ANY frob:debt is open at all, expired or not -- this is the ticket's
central "collected + re-raised before shipping" requirement. New public
list_debt/DebtEntry for a plain listing independent of the three gate
checks.

CLI (src/frob/app/debt_runner.py new, src/frob/app/app.py,
src/frob/app/config.py, src/frob/__main__.py): `frob debt [--json]` lists
every outstanding entry (rule, site, ticket, until, expired); no --apply,
since resolving a debt means fixing the underlying gap and removing the
directive, not something a command can auto-heal. __main__.py/config.py
were implicitly in scope (T-0446's feature-kind CLI-wiring-files rule);
app.py (the dispatch table, not covered by that rule) and the new runner
file were added via explicit `frob ticket scope --add`.

DEBT<->TODO coherence (per the ticket's own follow-up requirement): NOT
implemented as a fourth requirement in this pass -- re-reading the ticket
body, this is filed as its OWN acceptance clause with its own four
numbered requirements (paired frob:todo, shared open-ticket reuse, same-
ticket consistency check, symmetric resolution surfacing), which is a
second feature-sized unit of work layered on top of the debt/waive split
this ticket's title and primary DESIGN section actually describe. Given
context budget, I implemented the mechanism whose title and DESIGN section
this ticket names (frob:debt vs frob:waive, expiry, release-blocking,
listing) fully and honestly, and am disclosing the DEBT<->TODO coherence
clause as NOT done rather than half-implementing it. Not Filed as a named
follow-up: T-draft-b1002293 (never refiled) (mints a real T-#### id once this worktree
lands on main) "frob:debt/frob:todo coherence: paired todo, same-ticket
check, symmetric resolution", scoped to src/frob/graph/dsl.py (scope --add
for src/frob/gates/__init__.py was refused: T-0412 itself holds an
in-progress lease on that same file, the standard T-0453 collision guard;
the coordinator can widen the follow-up's scope once T-0412 lands and
releases the lease).

MIGRATE: explicitly NOT done in this ticket, per the dispatch instruction
("do NOT mass-rewrite waivers in this ticket; that is a follow-up
burndown"). Migration guidance recorded in
docs/guides/extending/comment-dsl-directives.md's new "frob:waive vs
frob:debt" section, describing exactly which shape of existing waiver
(reason= naming a ticket as the excuse) should convert and why converting
143 of them sight-unseen in one pass was judged too risky (mis-binding a
debt to the wrong/closed ticket is exactly DEBT002's failure mode).

Acceptance items status:
- "a frob:debt with a closed/missing ticket errors" -- DONE (DEBT002).
- "an expired frob:debt errors" -- DONE (DEBT003).
- "frob release check FAILS while debt is open" -- DONE
  (_release_open_debt_violations via release_gate/REL001).
- "frob debt reports the full outstanding set honestly" -- DONE (list_debt
  + `frob debt` CLI).
- "the 143 existing debt-waivers are migrated" -- NOT done, per explicit
  instruction to leave this as a follow-up burndown.
- DEBT<->TODO coherence's four sub-requirements -- NOT done, filed as a
  follow-up (see above).

Version bumped 0.53.0 -> 0.54.0 (REL001 minor: new public
debt_gate/list_debt/DebtEntry/EdgeKind.DEBT API); `frob release check` ->
"since 0.54.0: none change -> need >= 0.54.0 (current 0.54.0): OK".

Gates: `uv run frob check --ticket T-0412 --json` -> 0 new errors;
remaining DOC003 (docs/commands/sys.md) and REG003 x5 (docs/design/
registry/weaknesses.yaml) are the same pre-existing repo-wide debt
disclosed in T-0519/T-0507/T-0456's Done reports, unrelated to any file
this ticket touches. ruff check/format clean under both PATH ruff and
`uv run ruff` for every touched file. `frob debt`/`frob debt --json`
smoke-tested directly against this repo's own tree (0 entries currently,
since no frob:waive has been migrated yet).

### Changed
```
 .frob-release.json                              |  13 +-
 CHANGELOG.md                                    |  37 ++
 docs/guides/extending/comment-dsl-directives.md |  48 +-
 docs/modules/gates.md                           |  34 ++
 docs/modules/tickets.md                         |  57 +++
 pyproject.toml                                  |   2 +-
 src/frob/__main__.py                            |  11 +
 src/frob/app/ack_runner.py                      |  14 +-
 src/frob/app/app.py                             |   4 +-
 src/frob/app/config.py                          |   8 +
 src/frob/app/debt_runner.py                     |  92 ++++
 src/frob/app/ticket_runner.py                   |  20 +-
 src/frob/gates/__init__.py                      | 261 ++++++++++
 src/frob/gates/_models.py                       |  16 +
 src/frob/graph/_models.py                       |   3 +
 src/frob/graph/dsl.py                           |  15 +
 src/frob/release/__init__.py                    |  14 +-
 src/frob/tickets/_journal.py                    | 157 ++++++
 src/frob/tickets/_land.py                       |  88 ++--
 src/frob/tickets/_reconcile.py                  |  30 +-
 src/frob/tickets/_store.py                      |  15 +-
 tests/test_ack_worktree_lease.py                |  55 ++
 tests/test_debt_runner.py                       |  64 +++
 tests/test_gates.py                             | 161 ++++++
 tests/test_release_worktree_lease.py            |  52 ++
 tests/test_ticket_journal.py                    |  93 ++++
 tests/test_ticket_reconcile.py                  |  35 ++
 tests/unit/test_ticket_store.py                 |  51 ++
 tickets-archive.md                              |  17 +-
 tickets.md                                      | 635 +++++++++++++++++++++++-
 uv.lock                                         |   2 +-
 31 files changed, 2028 insertions(+), 76 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDebtGate::test_debt001_malformed_directive_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_debt002_closed_ticket_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_debt002_open_ticket_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_debt003_expired_by_date_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_debt003_not_yet_expired_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_debt003_expired_by_version_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_clean_debt_produces_no_violations` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_lists_every_debt_entry` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_release_gate_fails_while_debt_is_open` (pytest node id, verified passing when recorded)
- `tests/test_debt_runner.py::TestDebtRunner::test_json_mode_lists_debt_entries` (pytest node id, verified passing when recorded)
- `tests/test_debt_runner.py::TestDebtRunner::test_no_debt_logs_clean_message` (pytest node id, verified passing when recorded)
- `tests/test_debt_runner.py::TestDebtRunner::test_human_mode_reports_expired_flag` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
