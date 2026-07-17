---
id: T-0018
title: Convention-based unit-test binding inference to reduce frob:tests annotation
  burden
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/testing/**
evidence: []
attachments: []
---
Infer frob:tests unit bindings by naming convention (test_<symbol> -> <symbol>) as a default, with explicit frob:tests directives only needed to override or supplement. Reduces the annotation burden that COV001/TEST001 currently impose on every legacy module. Deferred post-0.1.0.