---
id: T-draft-b98ca434
title: 'frob ticket evidence --bind and docs-gate --bind: write directives from recorded
  evidence, never guess a binding'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4710
- T-4711
parent: T-4703
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
- src/frob/_cli_parsers/_ticket/_closeout_evidence.py
- docs/modules/tickets.md
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
Leaf 7 of T-4703. 2 points. Derived bindings: `--bind` on the evidence and docs surfaces.
Blocked by leaf 2 (it emits the multi-target form) and leaf 1 (it must write the declaration on
the side leaf 1 makes canonical). Scope is disjoint from every other leaf.

## What to build

(a) `frob ticket evidence <id> <node-id> --accepts N --bind` writes the `frob:tests` line for the
    accepted symbol FROM THE EVIDENCE IT ALREADY RECORDS -- the node id and the accepted symbol
    are both already in hand at that call site. Entry point: `_evidence` /
    `_evidence_apply_node_ids` in src/frob/app/ticket_runner/_verify.py:89-160; flag
    registration in src/frob/_cli_parsers/_ticket/_closeout_evidence.py alongside `--accepts`.
(b) The docs gates offer `--bind` for `frob:doc` where the anchor is ALREADY KNOWN (the gate
    resolved it to report the finding; writing it back is not a guess).
(c) The written line uses leaf 2's multi-target form when a binding already exists for that
    symbol -- append a target to the existing header rather than stacking a new line. This is
    what keeps `--bind` from recreating the stacks leaves 1 and 4 just removed.
(d) docs/modules/tickets.md and the evidence section of docs/modules/gates.md.

## Hard constraint (owner)

NO heuristic generator that guesses which test covers which symbol. Ever. `--bind` writes only
a binding that some other surface has ALREADY established and recorded. If the anchor or the
accepted symbol is not already known at the call site, `--bind` refuses with a message naming
what is missing -- it does not infer.

## Positive control

- Call `--bind` where the evidence records an accepted symbol: assert the exact expected
  `frob:tests` line, on the side leaf 1 makes canonical.
- Call `--bind` where the symbol is NOT determined: assert a refusal naming what is missing, and
  assert NO line is written. This is the control that `--bind` cannot degrade into a guesser.
- Call `--bind` twice for two targets of the same symbol: assert one multi-target header, not
  two stacked lines.
- Assert the written line round-trips through the parser to the edge the evidence describes.

## Acceptance

- `--bind` writes a correct, parseable directive from recorded evidence; refuses cleanly when
  the binding is not already known; never stacks.