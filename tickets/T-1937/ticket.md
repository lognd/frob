---
id: T-1937
title: 'Gate rule registry is not authoritative: 10 live rule ids bypass the acceptance
  preflight'
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_rule_id_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
AUDIT FINDING (full gate audit, 2026-08-09).

`_KNOWN_GATE_RULES` is documented as the AUTHORITY for which rule ids are
live, and `frob.tickets._new_gate_rule_acceptance` scrapes that literal's
SOURCE TEXT to detect newly-added rule ids for the T-0756 close/land
acceptance-policy preflight.

MEASURED: 288 quoted rule-id literals exist under src/; 9 are live but
absent from the registry -- BUDGET001, CHECK001, CVEFP001, DEPLOY001,
DEPLOY002, DEPLOY003, DERIVED001, SYS109, TIERBDEMO001. SYS104 is also
absent despite 390 ledger references and being mandatory since T-1113.

IMPACT: a soundness hole in a META-GATE. A rule added outside
SCANNED_BASES -- or in a construction shape the scan misses -- is
invisible to the acceptance preflight, so it ships WITHOUT the
acceptance-policy review that preflight exists to force. Two of the nine
(SYS109, TIERBDEMO001) live INSIDE src/frob/gates/ and were still missed,
so this is not only the disclosed out-of-base gap: shape detection leaks
within its own declared territory too.

The gap IS disclosed in `_rule_id_scan.py`'s docstring, but disclosure is
not enforcement -- it has since grown to 10 rules and nothing measures it.
Prefer making registry completeness self-checking across all of src/
(automatic) over documenting the caveat harder.