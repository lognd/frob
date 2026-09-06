---
id: T-4118
title: 'H3-6: a failure-injection test must assert on every response field, not only
  the field the test-plan row named'
state: queued
kind: ux
origin: human
created: '2026-09-06'
priority: critical
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_acceptance_template.py
- tests/unit/tickets/test_acceptance_template.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-307 H3-6 (verbatim, quoted at the bottom of T-4109's body). SITS APART from
the other nine per the parent epic's own classification: this is a PROCESS
rule about how a test-plan acceptance row gets written, not a code-analysis
rule. A prior audit already named the general shape ("a health/probe
component's test must inject a failing dependency") and a fix satisfied a
test-plan row ("reports db and redis") LITERALLY -- applying the failure-
injection assertion to the db field but never to the roll-up status field,
which stayed constant "ok" through the whole incident. The row was written
loosely, the fix matched it to the letter, and the wrong-incentive gap
between "satisfies the written row" and "actually asserts on everything the
row's INTENT covers" went unnoticed.

Work: this is a template/checklist fix, not a new AST-analysis gate --
locate wherever this repo's own ticket-acceptance-criteria authoring
guidance/template lives (the file this ticket's scope names is a starting
guess; confirm the real location during implementation and retarget scope
if the actual template lives elsewhere -- do not force the fix into the
named file if it turns out to be the wrong home) and add an explicit
authoring rule: a failure-injection acceptance criterion for a
health/probe/status-roll-up component must name EVERY field of the
response being asserted, not just the field under direct test, OR must
explicit call out which fields are deliberately excluded and why.
- if this repo has any existing lint that inspects test-plan/acceptance-
  criteria TEXT for shape (not test code) reuse it; otherwise this may
  ship as documentation-only (a written authoring rule plus a worked
  example) rather than a runnable check, per the parent epic's own
  characterization of this as a process rule -- decide which during
  implementation, document the choice in the Done report, and do not
  invent a speculative AST check against ticket prose that the rest of the
  gate set has no precedent for

Fixture note: DOES NOT FIT the must-fire/must-stay-quiet/third fixture
shape used by the other nine leaves, because this is process/prose
guidance, not a code-analysis rule with subjects to scan. If implementation
produces a runnable check, name its own fixture pair there; otherwise the
"fixture" for this leaf is a worked-example acceptance-criteria row (a
BAD one matching the H3-6 incident shape, and a GOOD one asserting every
response field) placed directly in the authoring guidance itself. FLAG
THIS EXPLICITLY as the one leaf of the ten that may ship with no automated
fixture at all.

frob:ticket T-4109