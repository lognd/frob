---
id: T-4710
title: frob:tests declared test-side only; graph derives the reverse edge, lint plus
  fix removes the production-side copy
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-4703
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
- src/frob/graph/__init__.py
- docs/modules/graph.md
- tests/unit/graph/test_dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'coordinator amendment (owner-approved): pin the move-path semantics and
    its refusal case as acceptance'
  actor: logan
  at: '2026-09-19'
  old_length: 3296
  new_length: 4354
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Leaf 1 of T-4703. 3 points. Move the `frob:tests` declaration to the test side and let the
graph derive the reverse edge, so the production-side copy stops existing. Sequenced FIRST
because it removes most stacks outright -- every later leaf's counts are measured after it.

## What to build

(a) Graph build derives symbol -> test edges from TEST-SIDE `frob:tests` declarations only.
    One declaration, one parse, canonical orientation emitted internally.
(b) A lint flags a `frob:tests` on a NON-TEST symbol as redundant, with a Tier-A fix that
    DELETES it when the test-side declaration already exists, and MOVES it to the test file
    when it does not -- so no coverage edge is ever lost.
(c) docs/modules/graph.md updated: the DSL's declaration side, the derived reverse edge, and
    the self-reference question settled below.

## Two contradictions this leaf must resolve (measured, cited, do not re-derive)

1. The TESTS edge is directional today: `src` is the implementation symbol the directive sits
   on, `target` is the test -- src/frob/gates/_tdd_order.py:465-487. TDD001 (T-4260)
   classifies an edge whose `src` looks like a test path and whose `target` does not as
   BACKWARDS, a malformed directive, and refuses an ordering verdict
   (src/frob/gates/_tdd_order.py:481-490). So the graph MUST emit the derived edge in the
   canonical implementation -> test orientation from a test-side declaration. Emitting the raw
   test-side orientation turns every migrated binding into a TDD001 backwards finding. This is
   the single highest-risk item in the leaf; write the test for it first.
2. src/frob/graph/dsl.py:1401-1420 documents `target == src` (a test naming itself) as a
   deliberate, widespread convention and does not reject it, while TDD001 T-4260 classifies
   `src == target` as malformed and skips it. Once declarations live test-side, the
   self-referential shape becomes the COMMON case. Settle which is right and say so in
   docs/modules/graph.md -- do not leave both standing.

Direction-agnostic consumer that will not notice either way (verified): src/frob/gates/
_coverage.py:420-426 unions both sides (`for side in (edge.src, edge.target)`).

## Positive control

- Plant a fixture with (i) a production symbol carrying `frob:tests`, no test-side
  declaration, (ii) a test-side declaration with no production copy, (iii) both. The fix must
  delete in case (iii), move in case (i), and no-op in case (ii). Assert the resulting edge
  set is byte-identical across all three.
- Plant a test-side declaration and assert TDD001 emits NO backwards finding for the derived
  edge -- the control for contradiction 1. Deliberately construct the raw-orientation variant
  and assert it WOULD have fired, so the test cannot pass vacuously.
- On the real repo: COV and TEST gate findings identical before and after, counts pasted into
  the Done report. Also paste the stack count (runs of 3+ consecutive directive lines) before
  and after: 1,712 is the before number.

## Acceptance

- Test-side declarations produce implementation -> test edges; zero new TDD001 findings.
- COV/TEST findings on the real repo identical before and after, counts in the Done report.
- Stack count with reverse copies removed, measured and reported against the 1,712 baseline.


## Move semantics (coordinator amendment, owner-approved) -- additional acceptance

When the Tier-A fix MOVES a production-side `frob:tests` to the test file (case (i): no
test-side declaration exists yet), it must:

- place the declaration DIRECTLY ABOVE the exact test node the id names, class-qualified --
  not at the top of the file, not above the class, not above a neighbouring test;
- REFUSE, reporting rather than fixing, when that node no longer exists in the test file. A
  dangling id is a finding for a human, never a binding to relocate by guess;
- NEVER invent a binding. The fix relocates exactly what the production-side directive already
  declared, verbatim; it derives nothing.

Acceptance for the move path specifically: COV and TEST gate findings are byte-for-byte
identical on the fixture before and after the move. Positive control: plant a production-side
`frob:tests` naming a node that does NOT exist and assert the fix refuses and reports, and that
the file is left byte-identical -- so the refusal path cannot pass vacuously.
