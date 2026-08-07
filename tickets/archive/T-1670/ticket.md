---
id: T-1670
title: 'frob ticket evidence: designate repro test explicitly + validate node-id shape
  at bind time'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner/**
- src/frob/gates/**
- docs/**
- tests/**
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: CLI flag + external-config allowlist wiring for --designate-repro
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/_config_external.py
  reason: CLI flag + external-config allowlist wiring for --designate-repro
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_gates_mutation_evidence.py::TestDesignatedReproTest::test_explicit_designation_wins_over_bind_order
- tests/test_gates_mutation_evidence.py::TestDesignatedReproTest::test_explicit_designation_not_in_evidence_falls_back_to_positional
- tests/test_ticket_evidence.py::TestSetDesignatedReproTest::test_designates_a_bound_evidence_id
- tests/test_ticket_evidence.py::TestSetDesignatedReproTest::test_refuses_an_id_not_in_evidence
designated_repro_test: null
threat: null
component: null
---
Two distinct evidence-binding defects, both currently diagnosed only at
land time, both recoverable but expensive to diagnose after the fact.

1. ORDER IS LOAD-BEARING AND INVISIBLE. `_designated_repro_test` in
   src/frob/gates/_mutation_evidence.py takes the FIRST pytest-node-id in
   `ticket.evidence` as the test BUG002 re-runs at the parent commit.
   Agents naturally bind pre-existing (already-passing-everywhere) tests
   first and their new repro test second, so the designated repro passes
   at parent and the land refuses -- not because the evidence is wrong,
   but because of bind ORDER, a property nothing in `frob ticket evidence`
   surfaces at bind time. Observed on T-1652, T-1653, T-1635. There is no
   reorder verb today -- the workaround is a `--replace` swap plus
   re-adding the displaced id.

   Fix: let a ticket DESIGNATE its repro test explicitly -- a flag on
   `frob ticket evidence` (e.g. `--designate-repro`) that marks one bound
   id as BUG002's designated test regardless of bind order, stored
   explicitly rather than inferred positionally. Surface which id is
   currently designated whenever evidence is shown (`frob ticket show`).

2. MALFORMED IDS ACCEPTED SILENTLY. This graph's convention is
   `path::Class.method` -- one `::` then a DOTTED class/method. Pytest's
   own `path::Class::method` form is accepted by `frob ticket evidence`
   without complaint and then fails DOC007, or fails to resolve post-merge
   and refuses the land.

   Fix: validate the node-id shape AT BIND TIME (`frob ticket evidence`)
   and reject the pytest `::`-separated form with a message naming the
   correct `path::Class.method` form. Also verify the referenced test
   actually exists (resolves against a real collected node id) at bind
   time, not just at close/land time.

Both parts turn a land-time diagnosis into an immediate, local error at
the point the mistake is made -- that is the whole point (filed from
T-1616's own mission text, which named this as follow-up work).