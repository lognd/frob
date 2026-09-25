---
id: T-draft-d750a6f1
title: 'GRAMMAR: `lattice` top-level declaration (trust/labels declarable in .strata)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-ffda706b
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- strata-core/src/parse/grammar_core.rs
- docs/strata/kernel.md#lattice-semantics
- src/frob/strata/_models.py (Lattice.__init__ desugar path)
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
OWNER-OWNED: strata surface change; owner reviews before dispatch


title: GRAMMAR: `lattice` top-level declaration (trust/labels declarable in .strata)
kind: feature (OWNER-OWNED)
tier: leaf
parent: T-SYS-SA
milestone: 0.539.0
sprint: sysdesign
points: 5
scope: strata-core/src/parse/grammar_core.rs, docs/strata/kernel.md#lattice-semantics,
       src/frob/strata/_models.py, tests/fixtures/sysdesign/lattice/**
blocked_by: []

Finding (STRATA-EXPRESSIVENESS.md, section E "principals/trust levels"):

"`Lattice` (TRUST = foreign<authenticated<trusted, LABELS = Public<Internal<Pii<Secret) is a
HARDCODED PYTHON CONSTANT in _models.py:67-76, not something a `.strata` file declares. The
surface grammar lets you USE these fixed levels (`node X : trusted`) but not DEFINE new ones or
a different lattice shape per-system. A mature system that needs a 4th trust tier (e.g.
'trusted-but-quarantined') or a differently-shaped label lattice cannot express it without an
owner-level change to _models.py, not a `.strata` edit."

"This is the single highest-leverage GRAMMAR gap found in this audit: almost every taxonomy
row above (tenancy isolation, compliance zones, environments dev/stage/prod) is a special case
of 'I need one more trust/label rung' and all are blocked on this same fixed-lattice
limitation."

Acceptance criteria:
- New grammar_core.rs production: `lattice trust { foreign < authenticated < trusted < ... }`
  (and the equivalent for LABELS), allowing a design module to extend or override TRUST/LABELS
  per-module instead of relying solely on the Python constant.
- `Lattice.__init__`'s existing cycle/duplicate-rung validation (_models.py:53) is reused as a
  per-file elaboration check against the declared lattice, not re-implemented.
- Backward compatibility: a `.strata` file with no `lattice` block continues to resolve against
  the existing Python-constant default lattice (no silent behavior change for the ~2900-line
  design/frob.strata self-model).
- docs/strata/kernel.md gets a new "#lattice-semantics" section documenting the declaration
  syntax and the default-lattice fallback rule.
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
- Positive-control fixture: tests/fixtures/sysdesign/lattice/quarantine-tier/design.strata
  declaring a 4th trust rung (`trusted-but-quarantined`) between `authenticated` and `trusted`,
  proving the new rung participates correctly in existing REL-family trust-boundary checks.

Downstream: every leaf across this epic that needs an additional trust/label rung (T-SYS-A
environment-axis note, SYSDESIGN rules for tenancy isolation and compliance zones in Story C/G)
is blocked_by this ticket, directly or by reference.
