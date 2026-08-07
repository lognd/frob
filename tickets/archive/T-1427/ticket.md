---
id: T-1427
title: Wire BUG002 (bug_repro_violations) into frob ticket land/close, register in
  _KNOWN_GATE_RULES
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/**
- src/frob/gates/_waive.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: '_KNOWN_GATE_RULES is defined in src/frob/gates/_waive.py, not

    src/frob/gates/__init__.py as the ticket brief assumed (__init__.py only

    imports/re-exports it at line 179). Registering "BUG002" requires editing

    the actual definition site.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/modules/gates.md
  reason: 'The dispatch brief explicitly requires updating docs/modules/gates.md''s

    BUG002 section (its "Scope note (disclosed cut)" paragraph describing "no

    caller yet" needs to be corrected now that this ticket wires one in).

    '
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_refuses_when_evidence_passes_at_parent
- tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_succeeds_when_evidence_fails_at_parent
designated_repro_test: null
threat: null
component: null
---
T-1421 built and tested `frob.gates._mutation_evidence.bug_repro_violations`
(BUG002: a bug/security ticket's designated evidence test must genuinely
FAIL at its parent commit) but, per T-1421's declared scope
(src/frob/gates/_mutation_evidence.py, tests/test_gates_mutation_evidence.py,
docs/modules/gates.md only), could not wire it into anything.

Two things remain, both outside T-1421's scope:

1. Register "BUG002" in `frob.gates._KNOWN_GATE_RULES` (currently in
   src/frob/gates/__init__.py) so the T-0756 new-gate-rule-acceptance
   preflight and the rule catalog both see it as a real, known rule id.

2. Wire `bug_repro_violations` into the same two call sites TEST016's
   `mutation_evidence_violations` already uses (same module, same
   established pattern -- see docs/modules/gates.md's BUG002 section):
   `frob.tickets._land._check_mutation_evidence` (frob ticket land
   precheck) and `frob.app.ticket_runner`'s direct `frob ticket close`
   CLI path (T-0844's precedent), so a bug/security ticket cannot
   close or land without the repro-at-parent check actually running.

Until this lands, BUG002 exists, is tested, and is documented, but does
not gate a real ticket close/land -- exactly the "built but not reachable"
gap docs/modules/gates.md's own T-0756 section warns about.