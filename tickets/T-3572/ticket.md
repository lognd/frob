---
id: T-3572
title: 'frob-arch type-dispatch-smell: _claims.py''s isinstance chain needs a real
  Protocol/dispatch design'
state: in-progress
kind: bug
origin: agent
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_claims.py
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
Filed while triaging T-3494 (frob-arch WARN remainder after T-2379). src/frob/strata/_claims.py:682, _eval_one_claim's 4-arm isinstance chain dispatches NoFlow/Reach/Independent/SetEquality (falling through to _eval_bound as the default case) to different _eval_* functions with DIFFERENT signatures (_eval_bound alone takes an extra current argument, unlike the other three). A mechanical dict-dispatch swap (the shape T-2379 used for src/frob/gates/_pii_structural/_keywords.py's _IDENTIFIER_NAME_EXTRACTORS) does not fit cleanly here because of the signature mismatch, and this is claim-body evaluation on strata's own proof-soundness critical path -- a rushed change to security-sensitive evaluation logic is the wrong way to clear a WARN-tier arch smell. Needs a proper Protocol (or a dispatch table with a uniform call signature, threading current through every arm even where unused today) design pass, with the existing claim-evaluation test suite as the regression floor -- not attempted here, deliberately deferred to its own dedicated ticket per T-3494's own investigation.
