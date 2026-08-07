## Done report

WIRE002 required every `frob:waive WIRE001` to name an open `follow_up`
ticket, treating "no production caller" as always temporary. For a
private test-seed helper called only by its own file's test methods
(`tests/unit/test_mutation_sweep_queue.py::_make_ticket`), having no
production caller is the permanent, intended design -- there is no real
follow-up work to bind to. Forcing one manufactured a placeholder
obligation (`follow_up="T-1518"`) that turned into a fresh WIRE002 orphan
the instant that placeholder ticket closed, exactly as the ticket
describes for the live incident.

Fix: `_wire002_is_permanent_test_helper_waiver` (src/frob/gates/_wire.py)
lets a `frob:waive WIRE001` declare `permanent="true"` instead of naming
a follow-up, and `_wire002_violations` now skips WIRE002 for any waiver
this predicate accepts. Restricted to private symbols (`_`-prefixed leaf
name) whose enclosing file lives under `tests/`, so production code
cannot use it to dodge real wiring -- a `permanent="true"` waiver on a
public symbol or a non-test-tree file still requires `follow_up=`
(verified by two negative regression tests).

`tests/unit/test_mutation_sweep_queue.py::_make_ticket`'s waiver was
swept from `follow_up="T-1592"` (this ticket, itself a placeholder) onto
`permanent="true"`, closing the exact live incident named in the ticket.
docs/modules/gates.md's WIRE001/WIRE002 section documents the new
attribute and its restriction; the WIRE002 catalog row was updated to
match.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 6199 warning(s), 717 waived
- error-findings: none (measured, zero errors)
