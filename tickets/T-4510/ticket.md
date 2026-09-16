---
id: T-4510
title: C# dup/docblock facet fixture (verify _CSHARP_LANGS bucket end to end)
state: queued
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4506
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/fixtures/csharp_dup_docblock/**
- tests/unit/test_support_csharp.py
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
src/frob/lang/_support.py already routes csharp through the _CSHARP_LANGS facet bucket (T-2906 _csharp_using_violations, T-3492) for capability/dup/docblock faceting, but there is no C# fixture proving dup-detection and docblock-checking actually fire correctly for csharp. Add a small fixture and test module.

GIVEN two near-duplicate C# methods in a fixture file, WHEN the dup detector runs, THEN it reports the duplicate pair using the _CSHARP_LANGS facet path.
GIVEN a public C# method missing an XML doc comment (///), WHEN the docblock checker runs, THEN it flags the missing docblock the same way it flags a missing Python docstring.
GIVEN a C# 'using' statement that _csharp_using_violations (T-2906) is meant to police, WHEN the checker runs on the fixture, THEN the expected violation fires with zero false positives on clean code.