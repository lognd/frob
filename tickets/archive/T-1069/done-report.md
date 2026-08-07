## Done report

Added set_tier(root, ticket_id, tier) in src/frob/tickets/__init__.py,
mirroring set_priority/set_kind/set_component/set_sprint's single-writer,
ledger-locked _set_ticket_field shape exactly -- same no-terminal-state-
check posture, same log-and-return contract. Wired frob ticket tier <id>
<epic|story|ticket> through _add_ticket_tier_parser (src/frob/__main__.py),
ticket_tier_value on AppConfig (src/frob/app/config.py), and _tier in
src/frob/app/ticket_runner.py's dispatch table, matching _priority/_kind's
"forward only, no re-derived validation" pattern -- an unknown tier value
raises inside TicketTier(...) and reports/exits the same way an
unresolvable ticket id does.

Verified end-to-end against a scratch ticket store (/tmp/frobtest):
`frob ticket tier T-0001 epic` flips the field and `frob ticket show`
reflects it; `frob ticket tier T-0001 bogus` reports the invalid-choice
error via argparse's own choices= validation before ever reaching
set_tier.

Extended T-1069's scope three times, each for a real touch this ticket's
own diff required: docs/modules/app.md and docs/design/registry/
EXHAUSTIVENESS-GATE.md (AFFECT001 flagged both as stale affects()-closure
docs once AppConfig/AppConfig.from_external/ticket_runner.run's digests
changed -- each doc got a real content addendum, not a no-op touch), and
tests/test_tickets_tiers.py (SCOPE001, since the new test class lives
there). Did NOT touch src/frob/tickets/_models.py -- TicketTier itself is
unchanged, only a new mutator over the existing enum.

Left two pre-existing, unrelated debt items alone rather than silently
fixing them under this ticket's scope: TICK006 (T-0667's Done report
names two now-unresolvable T-draft-* ids) and a long tail of SCOPE002
warnings from src/frob/__main__.py's whole-file scope glob (pre-existing
before this ticket touched the file) -- both already present on main,
confirmed via `git show main:tickets.md`.

Did NOT touch T-0936 (the EPIC-title ledger migration this ticket
unblocks) -- out of scope per the dispatch instructions; T-0936 remains
blocked_by=[T-1069] until this closes.

### Changed
```
 docs/design/registry/EXHAUSTIVENESS-GATE.md |   5 +-
 docs/modules/app.md                         |   7 +
 docs/modules/tickets.md                     |  24 ++-
 src/frob/__main__.py                        |  24 ++-
 src/frob/app/config.py                      |   7 +
 src/frob/app/ticket_runner.py               |  38 ++++-
 src/frob/tickets/__init__.py                |  20 +++
 tests/test_tickets_tiers.py                 |  74 ++++++++
 tickets.md                                  | 250 +++++++++++++++++++++++++++-
 9 files changed, 435 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_tickets_tiers.py::TestSetTier::test_updates_tier_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestSetTier::test_unknown_ticket_id_is_err` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestSetTier::test_structural_rules_apply_to_new_tier_on_next_read` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 4 error(s), 1117 warning(s), 420 waived
- error-findings: COV003@tickets/T-1063, COV003@tickets/T-1066, COV003@tickets/T-1073, TICK006@tickets.md
