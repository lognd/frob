## Done report

Closed the narrower, in-scope half of the asymmetry: `set_designated_repro_test`
(src/frob/tickets/_setters.py) now accepts an optional `reason` kwarg and
records a new `DesignatedReproChangeEntry` (src/frob/tickets/_models.py,
new `ticket.designated_repro_changes` field) whenever a REDESIGNATION
happens -- an already-set `designated_repro_test` changing to a
DIFFERENT bound id. A first-time designation, or a redundant
redesignation to the SAME id, appends nothing (mirroring
`replace_evidence`'s own "old==new is a no-op, not an audit event"
posture).

Closes the "no audit trail" half of the gap. Does NOT close the "no
--reason requirement" half: that needs a `--reason`/`--reason-file` CLI
flag (src/frob/_cli_parsers/_ticket/_closeout.py) threaded through
AppConfig (src/frob/app/config.py) -- both explicitly outside this
ticket's declared scope per dispatch instructions. Filed as a follow-up
(see Filed below).

Also fixed in passing (found while running this ticket's own unscoped
check): DOC001 on T-1554's new design doc (docs/design/
land-checkpoint-durability.md was linked from nowhere) -- linked it from
docs/index.md.

### Changed
```
 docs/index.md                      |   3 +
 src/frob/tickets/_models.py        |  43 ++++++++++++++
 src/frob/tickets/_setters.py       | 116 ++++++++++++++++++++++++++++++++-----
 tests/test_ticket_evidence.py      |  55 +++++++++++++++++-
 tickets/T-1554/ticket.md           |   7 +++
 tickets/T-1749/ticket.md           |  30 +++++++++-
 tickets/T-1851/ticket.md |  48 +++++++++++++++
 7 files changed, 285 insertions(+), 17 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 4 error(s), 852 warning(s), 742 waived
- error-findings: DOCENUM001@docs/modules/gates.md, PERF003@src/frob/strata/_policy.py, PERF004@src/frob/strata/_policy.py, SEC110@.claude/hooks/dispatch-telemetry.py
