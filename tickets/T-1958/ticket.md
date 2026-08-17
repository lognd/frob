---
id: T-1958
title: 'DOCENUM001: docs/modules/gates.md#rule-catalog stale after T-1937''s 8 new
  rule ids'
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1937 (landed 577c708436639342620efdd080d6667ee552db78) added 8 new rule
ids to src/frob/gates/_waive.py::_KNOWN_GATE_RULES (BUDGET001, CHECK001,
CVEFP001, DEPLOY001, DEPLOY002, DEPLOY003, DERIVED001, SYS109). T-1937's
own declared scope did not include docs/modules/gates.md, so the doc was
not updated in the same diff -- confirmed as a real, new gate ERROR by an
unscoped `frob check --only gates` measured immediately after the land:

  DOCENUM001 docs/modules/gates.md:13: frob:enumerates at
  docs/modules/gates.md#rule-catalog claims a stale member list for
  'src/frob/gates/_waive.py::_KNOWN_GATE_RULES' (doc omits: BUDGET001,
  CHECK001, CVEFP001, DEPLOY001, DEPLOY002, DEPLOY003, DERIVED001,
  SYS109)

Fix: add the 8 ids to docs/modules/gates.md's #rule-catalog enumeration
so the frob:enumerates directive is accurate again.

## Done report

Added the 8 ids T-1937 registered in _KNOWN_GATE_RULES (BUDGET001,
CHECK001, CVEFP001, DEPLOY001, DEPLOY002, DEPLOY003, DERIVED001, SYS109)
to docs/modules/gates.md's `frob:enumerates` members= list at
#rule-catalog, in the same sorted (python default string-sort) order the
existing list already uses -- verified this matches the gate's own
comparison (HOST-BLAST sorting before HOST001, VET-JS before VET-JS003,
etc, all consistent with plain codepoint ordering).

Measured before/after: `frob check --only docblocks` (DOCENUM001 lives
there, alongside DOC004/DOC005/DOC006/NEGEXIST001, per T-1227's
"no new stage-group registration needed" precedent) showed
`gate:DOC FAIL 1 errors` (the DOCENUM001 finding quoted in this ticket's
body) before the edit; after the edit, `gate:DOC pass 0 errors, 555
warnings, 0 waived`. The 2 remaining `gate:DRIFT` errors in that same run
are the pre-existing src/frob/tickets/_land.py DRIFT002 findings (T-1951/
T-1954's, not this ticket's scope, unaffected by this diff).

This is a docs-only change with no pytest surface of its own -- per
playbook section 5's T-0167 precedent, evidence is the existing CLI-
dispatch integration test.

Changed:
- docs/modules/gates.md (frob:enumerates members= list, +8 ids)

Evidence: tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
Gates: frob check --only docblocks clean of DOCENUM001 (0 errors on
gate:DOC); no other file touched.

### Changed
```
 tickets/T-1958/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 1118 warning(s), 705 waived
- error-findings: ARCH001@src/frob/gates/_dead_symbols.py, DOC002@src/frob/tickets/_land.py, DRIFT002@src/frob/tickets/_land.py
