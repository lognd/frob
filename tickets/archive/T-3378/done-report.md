## Done report

TICK002 self-deadlocked the fleet because close-time mirroring writes
an in-progress ticket's T-draft-* id onto main before its owning
ticket lands, so TICK002 fires by construction, raises quarantine, and
quarantine forces fully-synchronous verification fleet-wide -- blocking
every land, including the owning ticket's own, the ONLY land that
could ever clear the condition.

Fix: raise_quarantine now drops a TICK002 finding from the raise when
every T-draft-* id currently on the ledger is still owned by a live
(non-terminal) series (_draft_ids_all_have_live_owners), matching
candidate (a) from the ticket body -- encoded as a real exemption
mirroring the existing T-2132/T-3025 filter precedent in the same
function, rather than a per-incident manual quarantine dismissal. A
draft id that reached a terminal state (done/dropped) without ever
being promoted is deliberately NOT covered -- that is the genuine
promotion-failure shape TICK002 exists to catch, and it must keep
raising.

Kept the exemption predicate inside frob.verify (not a separate
frob.gates module, despite the ticket's named scope path) because
frob.verify has no declared cross-component Flow to frob.gates
(SYS003) and only the frob.tickets read (already-declared verify ->
tickets_ledger Flow, precedented by this same module's existing
load_queue late-import) was needed -- adding a new Flow to
design/frob.strata would be a separate, larger architecture decision
out of this bugfix's scope.

Added a must-fire test (TICK002 on a draft id with a live owner drops
out of the raise, is_quarantined stays False) and a must-stay-quiet
test (TICK002 on a draft id that reached DONE unpromoted still
raises). Full tests/unit/verify/test_quarantine.py: 37/37 pass. frob
test --base main: python exit=0.

### Changed
```
 tickets/T-3378/done-report.md | 48 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3378/ticket.md      | 22 ++++++++++++++++++--
 2 files changed, 68 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_tick002_dropped_when_every_draft_id_has_a_live_owner` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_tick002_still_raises_when_a_draft_id_is_terminal_unpromoted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 10 error(s), 4233 warning(s), 857 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
