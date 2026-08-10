## Done report

Found that `frob refactor rename` already detects and rewrites bound
evidence citations via `scan_evidence_citations`
(src/frob/refactor/_repointer.py, T-1200) -- but only against the legacy
`tickets.md`/`tickets-archive.md` monofiles. This repo migrated to
per-ticket files (`tickets/<id>/ticket.md`, `tickets/archive/<id>/
ticket.md`, T-1136 ledger-v2) as where evidence citations actually live
today, so the existing mechanism was silently stale against this repo's
own real ledger layout.

Fixed: `scan_evidence_citations` now also scans every
`tickets/<id>/ticket.md` and `tickets/archive/<id>/ticket.md` via
`_per_ticket_ledger_files`, in addition to the two legacy files. Two new
tests cover the live and archived per-ticket cases.

Not fixed here, filed as a follow-up: the rewrite this mechanism performs
is a raw text substitution, not a route through `replace_evidence`'s
`--reason`-required, audited path (T-1733) -- the actual "offer/auto-apply
the matching --replace rebind" T-1546's own body asked for. See Filed
below.

### Changed
```
 docs/index.md                      |   3 +
 rapid-debt.jsonl                   |   2 +
 src/frob/tickets/_models.py        |  43 ++++++++++++++
 src/frob/tickets/_setters.py       | 116 ++++++++++++++++++++++++++++++++-----
 tests/test_ticket_evidence.py      |  55 +++++++++++++++++-
 tickets/T-1546/ticket.md           |  34 ++++++++++-
 tickets/T-1554/ticket.md           |   7 +++
 tickets/T-1749/done-report.md      |  43 ++++++++++++++
 tickets/T-1749/ticket.md           |  38 +++++++++++-
 tickets/T-1838/ticket.md           |  17 ++++++
 tickets/T-1851/ticket.md           |  48 +++++++++++++++
 tickets/T-1854/ticket.md |  48 +++++++++++++++
 12 files changed, 433 insertions(+), 21 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 6 error(s), 740 warning(s), 743 waived
- error-findings: DOCENUM001@docs/modules/gates.md, PERF003@src/frob/strata/_policy.py, PERF004@src/frob/strata/_policy.py, SEC110@.claude/hooks/dispatch-telemetry.py, invalid-argument-type@src/frob/strata/_sync_may.py, invalid-type-form@src/frob/strata/_sync_may.py
