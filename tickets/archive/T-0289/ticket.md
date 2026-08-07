---
id: T-0289
title: 'arch: per-function reasoned override + complexity-aware long-function'
state: done
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/graph/dsl.py
- src/frob/gates/**
- tests/**
- docs/modules/arch.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_arch_gate.py::TestArchComplexityAware::test_flat_long_function_not_flagged
- tests/test_arch_gate.py::TestArchComplexityAware::test_complex_long_function_flagged
- tests/test_arch_gate.py::TestArchGateWaivers::test_reasoned_waive_honored
- tests/test_arch_gate.py::TestArchGateWaivers::test_unreasoned_waive_rejected
designated_repro_test: null
acceptance:
- text: 'given a genuinely atomic long function (big match/case, dispatch table, literal
    data, flat sequential pipeline) with low nesting/cyclomatic complexity, when frob
    arch runs, then it is NOT flagged (complexity-aware: long AND complex fires; long-but-flat
    does not)'
  evidence: []
- text: given a long function the author must keep long, when it carries a reasoned
    in-code directive (frob:waive ARCH001 reason="...", or frob:arch allow-long reason="..."
    ceiling=N), then the finding is WAIVED (counted in the waived tally, auditable),
    and an override without a reason is rejected exactly like a reasoned-less frob:waive
  evidence: []
- text: given a per-function override with a justified ceiling N, when the function
    later grows beyond N, then the waiver stops covering it and it re-fires (bounded,
    not a blank check)
  evidence: []
- text: given the escape hatch, then it lives at the code (in-comment directive travelling
    with the function), NOT as a qualname-keyed table in frob.toml, and raising the
    GLOBAL max_function_lines is not introduced as the sanctioned way to silence findings
  evidence: []
threat: null
component: null
---
User asked my opinion on per-function arch overrides. Opinion, recorded as the design: YES, worth having, but only if built the frob way. (1) Overrides belong AT THE CODE as reasoned frob:waive-style directives, not in central config -- a qualname table in frob.toml rots silently on rename and hides the exception from the reader; an in-comment waiver travels with the function and justifies the exception at its site, matching every other frob waiver. (2) It must be a WAIVER (counted, auditable, reason-required), never a silent mute -- an un-reasoned override is rejected like a reason-less frob:waive. (3) Prefer a justified CEILING bump over a boolean allow-long: a 45-line match waived to 50 still re-fires if it balloons to 200, keeping the exception honest. (4) Do NOT sanction raising the global threshold -- that is exactly the lazy-developer escape the tool exists to prevent. (5) MOST valuable half: make the heuristic complexity-aware so the bulk of false positives never fire -- a long-but-FLAT function (one match/dict-literal, shallow nesting, low cyclomatic) is not the smell the rule targets; only long-AND-complex is. Auto-exempt flat, require a reasoned waiver for the complex-but-justified residue. This also relieves the arch<->dup tension (T-0288): stop forcing atomic bodies to shatter into helpers that then hide/duplicate.