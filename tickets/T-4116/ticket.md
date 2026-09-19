---
id: T-4116
title: 'H3-4: a symbol docstring claiming never/always/idempotent with no bound invariant
  is an unverified claim'
state: done
kind: invariant
origin: human
created: '2026-09-06'
priority: critical
parent: T-4109
tier: ticket
sprint: v0.541.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_claim_lint.py
- tests/gates_suite/test_claim_lint.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-4111 lease released; CLAIM001 doc row required by coordinator checklist
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.541.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-13'
evidence:
- tests/gates_suite/test_claim_lint.py::test_claim001_fires_on_unbound_never_claim
- tests/gates_suite/test_claim_lint.py::test_claim001_quiet_when_invariant_directive_present
- tests/gates_suite/test_claim_lint.py::test_claim001_quiet_on_ordinary_prose_regardless_of_invariant_coverage
- tests/gates_suite/test_claim_lint.py::test_claim001_honors_frob_waive_escape_hatch
- tests/gates_suite/test_claim_lint.py::test_claim001_fires_once_per_offending_symbol_not_per_word
- tests/gates_suite/test_claim_lint.py::test_claim001_scopes_to_the_exact_symbol_not_the_whole_file
- tests/gates_suite/test_claim_lint.py::test_claim001_fires_on_class_docstring_too
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-307 H3-4 (verbatim, quoted at the bottom of T-4109's body). A docstring
asserted "never raises" three times in one file, bound to zero
frob:invariant markers or property tests -- exactly the gap frob:invariant
plus the prove loop exist for, but nothing flags the UNBOUND CLAIM itself; a
full invariant-coverage sweep only ever measures claims someone already
marked. Proposed rule: flag a docstring on a SYMBOL (function/method/class)
asserting never/always/idempotent-shaped language when that symbol carries
no frob:invariant directive -- a cheap lint that catches the claim, which is
also the case where the claim is FALSE and no one has checked.

Per the parent epic's explicit caution: this is NOT the same comparison as
H3-9 (module docstring vs the module's own code) -- keep them separate
leaves. This leaf's comparison is: symbol docstring text vs. that SAME
symbol's own frob:invariant binding (a directive-presence check, not a
code-behavior check).

Work:
- a text-pattern lint (regex or lightweight NLP-free keyword match, this
  repo's existing convention for this kind of prose-claim scan -- follow
  whatever pattern _lexical_selfcheck.py or similar existing lints in
  src/frob/gates/ already use for a keyword-in-docstring shape, rather than
  inventing a new scanning idiom) over every public AND private symbol's
  docstring for never/always/idempotent (case-insensitive, whole-word)
- WARN-tier finding when such language is present and the symbol carries no
  frob:invariant directive anywhere in its own span
- standard frob:waive escape hatch for a claim that is genuinely covered by
  a differently-shaped test the directive convention cannot see

Fixture note: this fires cleanly in frob's own tree -- frob's own codebase
has plenty of docstrings using never/always language (this ticket's own
grounding search surfaced several in unrelated modules), so a real
must-fire instance likely already exists; use a synthetic pair in the test
file regardless for a controlled, non-flaky assertion:
- must-fire: a function whose docstring says "this never raises" with no
  frob:invariant directive anywhere in its span
- must-stay-quiet: the same docstring text, but WITH a frob:invariant
  directive present
- third: a function whose docstring does NOT use never/always/idempotent
  language at all (ordinary prose) -- must stay quiet regardless of
  invariant coverage, since this lint is claim-triggered, not universal

frob:ticket T-4109