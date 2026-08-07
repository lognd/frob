---
id: T-1039
title: promote OPAQUE001 to ERROR-tier once frob's own 93-site first-turn-on set is
  fixed-or-waived
state: dropped
kind: security
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_opaque.py
- src/frob/vet/**
- src/frob/app/config.py
- src/frob/deploy/**
- src/frob/dup/**
- src/frob/fuzz/**
- src/frob/graph/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-0665 landed OPAQUE001 (frob.gates._opaque.opaque_gate) at WARN-tier
per the T-0688/T-0973 first-turn-on promotion precedent: a first
measurement against frob's own tracked codebase found 93 real sites
after string-literal/comment false-positive filtering (147 before),
concentrated in test fixtures using dynamic getattr/setattr for
monkeypatch-style assertions, plus a handful of production sites
(src/frob/app/config.py, src/frob/deploy/_conform.py,
src/frob/dup/_pipeline.py, src/frob/fuzz/_signatures.py,
src/frob/graph/lock.py, src/frob/vet/_capability.py itself). This is
above the >25-site WARN-first threshold, so promoting straight to
ERROR was not safe to do in the same ticket.

Scope: audit each of the ~93 sites and either (a) rewrite to a static
name where the dynamic lookup was incidental, or (b) add an honest
`frob:waive OPAQUE001 reason="..."` naming why the site is a legitimate
runtime-resolved indirection (most test-fixture sites will fall here --
mock/monkeypatch dynamic attribute access is often intentional test
infrastructure, not an evasion risk). Once the WARN count reaches zero
real (unwaived) findings, promote opaque_gate's Severity from WARN to
ERROR in src/frob/gates/_opaque.py.

## Drop reason
- 2026-07-28: exact duplicate of T-1038 (identical title, body, scope) tracking the same OPAQUE001 WARN->ERROR promotion; T-1038 remains the active tracking ticket