---
id: T-3975
title: evidence satisfaction must exclude xfail/xpass/skip by default
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-3928
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the current outcome-handling code, when this ticket's first step runs,
    then it reports whether xfail/xpass/skip currently satisfy evidence in this repo
    before any code change
  evidence: []
- text: given the fix, when a test outcome is xfail/xpass/skipped and no explicit
    opt-in is declared, then it does not satisfy frob:tests or ticket evidence
  evidence: []
- text: given an explicit opt-in is declared, when such an outcome occurs, then it
    is reported as a distinct countable state, not folded into passed
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3928 edge/ops-unique item. THIS ONE BEARS ON FROB'S OWN EVIDENCE INTEGRITY, per the epic's own framing -- if xfail/xpass/skip satisfies frob:tests or ticket evidence today, every fail-then-pass claim this repo's own gates rely on is weaker than it reads.

FINDING THIS WOULD HAVE CAUGHT: a process gate that pytest-xfails away every violation and can never fail, and a component whose whole suite skips when a toolchain is absent -- both counted as passing evidence in the consumer's frob:tests/ticket-evidence bindings.

VERIFY FIRST (before building): read src/frob/testing/_models.py and _runners.py's outcome handling -- does the current evidence-satisfaction check accept outcome states other than "passed" today (xfail, xpass, skipped)? This is a claim about our own code and must be measured, not assumed, before deciding whether this is a real gap here too or only in the consumer's own pytest config.

Proposed default: evidence satisfaction requires outcome==passed; an explicit opt-in for xfail/skip-as-evidence must exist as a distinct, COUNTABLE state (reported separately, not folded into "green") rather than silently accepted as equivalent to passed.
