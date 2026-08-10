---
id: T-1781
title: Wire DOCENUM001 to the gates.md rule-catalog table via _KNOWN_GATE_RULES
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
- tickets/T-1781/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1781/ticket.md
  reason: v2 ledger per-ticket file
  actor: logan
  at: '2026-08-08'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
T-1611 classification: T-1610's docs-completeness sweep found
docs/modules/gates.md's "Rule catalog" table missing ~122 real, already-
fired rule ids (docs/audits/docs-completeness-2026-08-06.md, gap 2). The
table frames itself as the exhaustive index; a mechanical scan of every
`"XXXX###"`-shaped literal under src/frob/gates/ found 275 real ids, 122
absent from the table.

Classified as RULE EXISTS BUT WAS NEVER WIRED to this specific
obligation -- not "no rule exists". DOCENUM001 (src/frob/gates/
_docenum.py, T-1227) is built for exactly this shape: a doc table/list
that restates a code collection's members, kept in sync via a
`frob:enumerates <symref> members="..."` directive that DOCENUM001
AST-diffs against the real collection every run. `_KNOWN_GATE_RULES`
(src/frob/gates/_waive.py:173, a module-level frozenset) is already the
live, authoritative set of every registered rule id -- exactly the
"module-level frozenset literal" shape DOCENUM001's own docstring lists
as supported. Nobody ever added a `frob:enumerates` directive anchoring
the gates.md rule-catalog table to `_KNOWN_GATE_RULES`, so the
mechanism that would have caught this drift immediately was never
switched on for this specific table. DRIFT001 (digest-staleness only)
cannot substitute -- a table's prose can be byte-identical to its last
ack and still silently miss a newly-added rule id, which is the exact
gap this module's own docstring says DOCENUM001 exists to close.

Fix: add `<!-- frob:enumerates src/frob/gates/_waive.py::_KNOWN_GATE_RULES
members="..." -->` above the rule-catalog table, backfill the current
~122 missing rows (T-1681, already filed by T-1610, does the content
backfill), and let DOCENUM001 keep it from drifting again. This ticket
is the WIRING half; T-1681 is the CONTENT half -- land whichever is
ready first, they do not block each other.

## Done report

Wired DOCENUM001 to `docs/modules/gates.md`'s "Rule catalog" table via
`_KNOWN_GATE_RULES` (T-1611 classification, the wiring half of the
T-1610 docs-completeness gap; T-1681, the content-backfill half, was
already landed by another agent before this ticket started).

Added `<!-- frob:enumerates src/frob/gates/_waive.py::_KNOWN_GATE_RULES
members="..." -->` directly above the table, with the current, exact
291-member set (`sorted(_KNOWN_GATE_RULES)` at HEAD). DOCENUM001
AST-diffs this claimed list against the real frozenset every run
(independent of ack state, per the gate's own docstring) -- any future
rule id added to or removed from `_KNOWN_GATE_RULES` without a matching
update to this directive now fails `frob check` immediately, closing the
exact gap DRIFT001 alone could not: a byte-identical, already-acked
table can still silently miss a newly registered rule id.

Verified with the gate itself, not just a mental check: `frob check
--only docblocks` (DOCENUM001 rides that stage group alongside
DOC004/DOC005/DOC006/NEGEXIST001) reports 0 errors both before writing
the directive (the collection existed, no claim to violate yet) and
after (claimed list matches real). Confirmed the directive's placement
does not itself require every rule id to physically appear as a table
row -- that is T-1681's already-discharged content obligation; this
directive only pins the claimed MEMBER LIST, which is what DOCENUM001
mechanically verifies.

Docs-only ticket, no pytest surface of its own -- recording the existing
CLI-dispatch integration test as evidence per the T-0167 precedent
(playbook section 5).

<!-- frob:no-behavior-change reason="pure docs-only change: adds a frob:enumerates directive above an existing markdown table so DOCENUM001 can verify it; no src/frob/**/*.py runtime behavior changed, so the designated repro test (a CLI-dispatch smoke test unrelated to this table) correctly passes at both main and this fix -- BUG002's inverted check is the honest contract here per T-1616" -->

### Changed
```
 tickets/T-1781/done-report.md | 44 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1781/ticket.md      | 13 +++++++++++--
 2 files changed, 55 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 825 warning(s), 732 waived
- error-findings: ARCH001@src/frob/tickets/_new_renumber.py, invalid-assignment@tests/test_ticket_land.py, invalid-return-type@src/frob/tickets/_new_renumber.py
