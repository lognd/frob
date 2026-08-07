---
id: T-0268
title: 'fix(frob-core): candidate_pairs can return a self-pair (i, i)'
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- frob-core/src/lib.rs
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_dup_core.py::test_candidate_pairs_never_returns_a_self_pair
designated_repro_test: null
threat: null
component: null
---
Found while working T-0191: frob_core::candidate_pairs can hand back (i, i) when a symbol's own R4 winnowed-fingerprint set collides with itself past the shared-token floor -- observed for real on this repo's own dup cache module (DUP002 reported get_verdict as its own clone). T-0191 guarded the one Python-side consumer (_r4_groups in src/frob/dup/_pipeline.py) with an i==j/a==b skip, but the kernel itself still emits self-pairs, so any OTHER caller of candidate_pairs inherits the same footgun unless it also guards. Fix at the kernel (skip i==j in the Rust candidate-pair emission) so every caller gets it for free.