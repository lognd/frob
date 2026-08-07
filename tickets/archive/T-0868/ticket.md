---
id: T-0868
title: typestate state-requirement verification + recorded language-excuse discharges
state: dropped
kind: security
origin: human
created: '2026-07-23'
priority: high
blocked_by:
- T-0866
- T-0867
parent: T-0739
tier: ticket
sprint: null
scope:
- src/frob/arch/_typestate.py
- src/frob/gates/**
- tests/unit/test_typestate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN a fixture calling a state-requiring function with no path establishing
    that state WHEN frob check runs THEN the typestate violation fires naming the
    function, the required state, and the witness path
  evidence: []
- text: GIVEN a fixture whose deinit obligation is discharged by a recorded language
    mechanism (Rust Drop, C++ RAII holder, Python with-block) WHEN frob check runs
    THEN the obligation is discharged with the mechanism named, and a GC-finalizer-only
    fixture is NOT discharged
  evidence: []
threat: null
component: arch
---
T-0739 child 3 (verification + excuses). State-requirement verification: a function valid only in state S must be unreachable on paths where S is not established (init-never-called class; TCP-handshake-style ordering). Language excuses are recorded DISCHARGES naming their mechanism per T-0383 caught_by doctrine: Rust Drop unless mem::forget observed; C++ RAII only when the init result is held by a destructor-bearing object; Python with-blocks count, GC finalizers NEVER count; TS using/try-finally. Declared LIMITS (no aliased per-object heap typestate; concurrency races belong to the T-0693 family) documented, not silently absorbed.

## Drop reason
- 2026-07-23: duplicate of the pre-existing T-0739 child set (T-0744/T-0745/T-0746/T-0747, mostly done) -- filed 2026-07-23 without checking parent-edge children; typestate declaration surface, summary engine, verification+excuses already delivered in graph/dsl.py, graph/summary.py, gates/_protocol_summary.py