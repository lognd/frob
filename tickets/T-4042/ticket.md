---
id: T-4042
title: 'F-241: a pytest-shaped id validator rejects legitimate deep cargo ids our
  own collector produced, forcing a consumer to restructure source'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/__init__.py
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
Consumer logand.app-v2 F-241, 2026-09-06:

  "T-0216 had to FLATTEN A NESTED TEST MODULE (token_json tests inside
   color.rs::tests) because `frob ticket evidence` refused
   `file.rs::tests::inner::name` ids that appear VERBATIM in
   cargo-collect.json. Accept the collector's own ids unchanged."

THE TOOL FORCED A SOURCE-CODE RESTRUCTURING. That is the headline. A consumer
changed the shape of their real Rust test module -- not a comment, not a
directive, actual code organisation -- to satisfy an id validator. Nothing about
their nesting was wrong; frob simply could not express it. That is the most
expensive kind of tooling defect, because the damage persists in their codebase
after any fix we ship.

VERIFIED IN OUR SOURCE, and the docstring convicts itself.
src/frob/tickets/__init__.py:552, `_has_excess_separator_segments` (T-1706):

    """`True` when `entry` has THREE OR MORE `::`-separated segments (e.g.
    `path::Class::method::extra`) -- A SHAPE NO REAL PYTEST NODE ID OR `cmd:`
    EVIDENCE ENTRY EVER TAKES (T-1706)."""

    _, _, remainder = entry.partition("::")
    return remainder.count("::") >= 2

The justification is explicitly and only about PYTEST. Within Python it is
correct: a pytest id really does not go deeper than path::Class::method. It was
then applied to every language. Cargo emits arbitrarily deep module paths --
`file.rs::tests::inner::name` is ordinary, and our own collector WROTE it into
cargo-collect.json before the binder refused it.

SO THE COLLECTOR AND THE VALIDATOR DISAGREE ABOUT WHAT A VALID ID IS. One half of
frob produced the id; the other half rejected it as malformed. That desync is the
actual defect, and it is worse than a missing feature: the system contradicts
itself and blames the user.

THIS IS THE SIXTH CONFIRMED PYTHON-DEFAULT INSTANCE, all filed:
  T-3945  normalize_evidence_separator mangles dotted kotlin ids
  T-3981  an unresolved rust id is told "this test does not exist in this tree"
  T-3999  close reaches for a pytest verdict on rust-only evidence
  T-3937  (with T-3925) binding resolved only python and rust for a long time
  T-4016  the TS walker emits no symbol for describe()/it()
  this    a pytest-shaped validator rejects legitimate cargo ids
Six call sites independently assuming python. WHOEVER TAKES THIS SHOULD ASK
WHETHER A SHARED "what language is this id, and what shapes are legal for it"
HELPER EXISTS -- six places each answering that question separately is exactly
how this keeps recurring. LANGUAGE_COLLECTORS is already the one registry of
languages; id-shape validation should hang off the same place.

THE FIX, in the consumer's own words: accept the collector's own ids unchanged.
The authority on whether an id is well-formed is the collector that produced it,
not a hand-written shape rule. If validation is still wanted, validate PER
LANGUAGE against that language's collector, or simply require that the id
resolves against a collected set -- which is a stronger check than a segment
count and is already implemented.

DO NOT fix this by raising the segment limit to three or four. That repeats the
error one level out: cargo nesting is unbounded, and any constant is a guess
about someone else's module layout.

BE CAREFUL WHAT T-1706 WAS PROTECTING. It exists to catch genuinely malformed
ids, and that intent is legitimate -- read that ticket before removing the
check so the original failure mode does not return. The fix is to make the
check language-aware, not to delete it.

MUST-FIRE FIXTURE: a genuinely malformed id (the shape T-1706 was written for) is
still rejected.
MUST-STAY-QUIET: a deep cargo id present verbatim in cargo-collect.json binds
successfully, with no source restructuring required.
THIRD FIXTURE: an id produced by ANY registered collector is accepted by the
binder -- collector and validator agree by construction, not by coincidence.

ACCEPTANCE
- Id-shape validation is language-aware, derived from the collector registry
  rather than a hand-written pytest assumption.
- T-1706's original failure mode still caught, proven by fixture.
- All three fixtures committed.