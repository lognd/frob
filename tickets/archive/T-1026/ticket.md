---
id: T-1026
title: sequential-independent-awaits should suggest asyncio.gather (T-0698 disclosed
  cut)
state: dropped
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-0698's own text names a fourth advisory shape ("sequential awaits over
independent IO -> suggest gather") this ticket's implementation did not
build: proving two `await` expressions are INDEPENDENT (neither reads a
value the other produced) needs a data-dependency analysis this repo's
current `frob.arch` normalized model does not yet provide (NormalizedCall
tracks a call's own bare-identifier arguments, not a cross-statement
def-use chain). Approximating "independent" as "textually adjacent await
statements" would risk false positives on genuinely sequential
awaits (the second explicitly depends on the first's result) -- an
unsound advisory is worse than no advisory for this repo's own
noise-discipline convention (T-0332).

Scope for this follow-up: `src/frob/arch/**`, `tests/unit/test_arch.py`,
`docs/modules/arch.md`. Build a minimal def-use check over two or more
sequential `await` statements in the same function body: an `await`
whose LHS binding is never read by any argument of a LATER `await`
expression in the same own-scope sequence is "independent"; suggest
`asyncio.gather` naming the awaited call sites. Same advisory-tier,
unwaivable-channel posture as every other T-0693 concurrency-hazard
category.

## Drop reason
- 2026-07-27: accidental duplicate filing (double invocation), see T-1027 (absorbed by T-1027)