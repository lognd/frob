---
id: T-draft-7d961cd5
title: 'WIRE the boundary admit block: parsed into AdmitPhase and read by nothing,
  while _backpressure.py regex-infers the same quantity from source'
state: queued
kind: feature
origin: agent
created: '2026-09-19'
priority: high
parent: T-4666
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_elaborate.py
- src/frob/strata/_backpressure.py
- tests/unit/strata/test_admit_phase_wiring.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given admit/rate_limit/max_size/judge are the audit's 4 DEAD-CANDIDATE keywords
    -- parsed at grammar_flow.rs:206-236, modelled at _ast.py:341 AdmitPhase, and
    read by nothing (git grep -wn admit over src/frob/strata and src/frob/gates returns
    only the AST definition and prose) -- when this lands, then _elaborate.py validates
    the admit phase alongside the existing parse/effect/record/refuse validators in
    _validate_boundary_phases.
  evidence: []
- text: Given _backpressure.py:105-110 infers bounded intake from source text with
    _BOUNDED_INTAKE_TOKEN_RE, whose own comment concedes it is 'not a claim the matched
    token bounds the SAME queue the node models', when this lands, then a declared
    admit rate_limit CHANGES the backpressure ceiling -- a positive control using
    a model whose bound code contains NO bounded-intake token, which fails at HEAD
    where the declaration is parsed and then ignored.
  evidence: []
- text: Given the regex path must survive for models that declare no admit block,
    when no admit block is declared, then a test asserts the regex inference still
    applies, and the code logs at INFO which path produced the verdict so a backpressure
    result always says whether it was declared or guessed.
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
WIRE leaf from the pessimistic keyword audit (scratchpad/STRATA-KEYWORDS.md),
under T-4678's decision: nothing is deleted, dormant constructs are wired.
Story points: 3. IMMEDIATELY DISPATCHABLE -- no blockers.

THE FINDING. All 4 of the audit's DEAD-CANDIDATE keywords are the boundary
`admit` block. They are parsed, modelled in the AST, and read by NOTHING.

| kw | parsed | AST node | reader |
|---|---|---|---|
| `admit` | strata-core/src/parse/grammar_flow.rs:206 | _ast.py:341 `AdmitPhase` | none |
| `rate_limit` | grammar_flow.rs:222 | _ast.py:346 | none (only a regex string in _backpressure.py) |
| `max_size` | grammar_flow.rs:225 | _ast.py:347 | none (only _backpressure.py) |
| `judge` | grammar_flow.rs:271 | `PhaseBlock.judge: bool` | none |

Planner-verified at HEAD:
- src/frob/strata/_ast.py:341-347 defines `AdmitPhase` with `rate_limit:
  Quantity | None` and `max_size: Quantity | None`, docstring "A parsed
  `admit { rate_limit ...; max_size ... }` boundary phase block."
- `git grep -wn admit -- src/frob/strata src/frob/gates` returns only the AST
  definition, `PhaseBlock.admit` at _ast.py:405, and PROSE in _elaborate.py:644,
  :899, _errors.py:38, :104, _deploy.py. No validator, no flow, no consumer.
- src/frob/strata/_elaborate.py:899 admits the gap in its own docstring:
  "`admit`, `parse`, `judge`, and `refuse` carry no flow of their own in v0 --
  validation of their structural rules happens in `_validate_boundary_phases`".
  But `_validate_boundary_phases` validates only `parse`, `effect`, `record` and
  `refuse`. **`admit` and `judge` have no validator and no flow.**

THE SHARP PART. `admit { rate_limit N req/s; max_size N KB }` is EXACTLY the
declaration that src/frob/strata/_backpressure.py currently INFERS FROM SOURCE
TEXT WITH A REGEX. `_BOUNDED_INTAKE_TOKEN_RE` (_backpressure.py:105-110) scans
for `max_size=`, `Semaphore(`, `BoundedSemaphore(`, `backpressure`,
`bounded_queue`, `token_bucket`, `rate_limit` tokens, and its own comment
concedes the honesty limit: "not a claim the matched token bounds the SAME queue
the node models, only that the node's bound code contains real evidence of a
bounded-intake construct." So the model has a precise declared answer available
and the gate guesses instead.

WHAT TO BUILD
1. A validator for `admit` in src/frob/strata/_elaborate.py, alongside the
   existing parse/effect/record/refuse validators in `_validate_boundary_phases`.
2. Emit the admit quantities as kernel facts -- `Bound(rate, boundary) <=
   rate_limit` and `Bound(size, boundary) <= max_size` -- so they reach the
   prover as Bounds rather than as a Python-side special case. Bound is one of
   the six primitives, so this is desugaring, not a kernel extension, and needs
   no law-1 record.
3. Make src/frob/strata/_backpressure.py PREFER a declared admit block over its
   regex inference, falling back to the regex only where no admit block is
   declared. Log which path produced the verdict at INFO -- per
   memory/silent-zero-is-the-dominant-bug-class.md, a backpressure verdict that
   does not say whether it was declared or guessed is not a measurement.

`judge` is deliberately OUT of scope here: the audit says it needs either a
`Flow(condition=phase)` like `effect` gets, or folding into `effect`, and that
is a design question rather than a wiring one. Do not guess it; if the admit
work makes the answer obvious, record it and file it.

POSITIVE CONTROL (the test that fails today)
A litmus/fixture model declaring `admit { rate_limit N req/s }` on a boundary
whose bound code contains NO bounded-intake token, asserted to CHANGE the
backpressure ceiling. It fails at HEAD, where the declaration is parsed into
`AdmitPhase` and then ignored entirely. Add the converse control too: a node
whose declared admit block is ABSENT still falls back to the regex path, so this
leaf cannot be satisfied by deleting the inference.
