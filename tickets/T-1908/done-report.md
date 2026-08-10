## Done report

Read the real implementations before classifying: `_debt` (T-1570)
delegates to `frob.app.debt_runner.run`, whose own module docstring says
"It never mutates anything (no `--apply` ...)"; `_deprecated` (T-1570)
delegates to `frob.app.deprecated_runner.run`, same shape/same
no-`--apply` docstring; `_wave` (T-1738) only calls `load_queue` and
`frob.tickets._doable.wave` to render doable-set groups -- no
`write_ticket`/`_set_ticket_field` call anywhere in it. All three are
listing/rendering only, so all three belong in `_READ_ONLY_VERBS`, not
`_MUTATING_VERB_INVOCATIONS`.

On whether this test can fail at verb-ADD time instead of later: yes, in
principle, but not for free within this ticket's scope
(tests/test_ticket_leases.py only). The dispatch table
(`frob.app.ticket_runner._ticket_dispatch_table`) and the classification
buckets currently live in different files with no shared source of
truth -- a verb can be added to one without the other by construction.
Options that would make drift impossible rather than merely detected
one CI run later:
  1. Colocate the classification as a decorator/registry entry at each
     handler's own definition site (e.g. `@read_only` /
     `@mutating(invocation=...)` on `_debt`/`_wave`/etc. in
     ticket_runner), and have `_ticket_dispatch_table()` build itself
     FROM that registry -- a new verb without a classification would
     fail to import/register at all, not just fail a test.
  2. A frob-native answer fits this repo's own model better: an
     `frob:invariant` or `frob:ticket`-style directive requirement on
     every dispatch-table handler, enforced by a gate rule (ARCH-shaped)
     that fails `frob check` the moment a handler function lacks a
     classification directive -- this is caught at `frob check` time on
     the SAME commit that adds the verb, not discovered later by whoever
     next runs this specific test file.
  Both are structural changes to `frob.app.ticket_runner` (the dispatch
  table's own module) and to `frob.gates` for option 2 -- outside this
  ticket's `tests/test_ticket_leases.py` scope to implement. Filing this
  analysis in the Done report per the dispatch note; a follow-up ticket
  should own whichever option T-1887's Tier-A signature-ticket precedent
  favors.

### Changed
```
 docs/modules/gates.md         | 41 +++++++++++++++++++++++++++++++++++++++++
 frob.lock                     | 14 ++++++++++++++
 rapid-debt.jsonl              |  1 +
 tests/test_ticket_leases.py   | 21 ++++++++++++++++++++-
 tickets/T-1893/done-report.md | 37 +++++++++++++++++++++++++++++++++++++
 tickets/T-1893/ticket.md      | 15 +++++++++++++--
 tickets/T-1908/ticket.md      |  2 +-
 7 files changed, 127 insertions(+), 4 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 1 error(s), 869 warning(s), 695 waived
- error-findings: REG002@docs/design/registry/check-coverage.yaml
