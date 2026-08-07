---
id: T-0018
title: Convention-based unit-test binding inference to reduce frob:tests annotation
  burden
state: dropped
kind: feature
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Infer frob:tests unit bindings by naming convention (test_<symbol> -> <symbol>) as a default, with explicit frob:tests directives only needed to override or supplement. Reduces the annotation burden that COV001/TEST001 currently impose on every legacy module. Deferred post-0.1.0.

Delivered under T-0039.