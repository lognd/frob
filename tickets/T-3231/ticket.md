---
id: T-3231
title: 'EPIC refactor multi-language: per-language reference scanners'
state: queued
kind: feature
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/**
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
T-2996 found frob.refactor (move-module/move-symbol) is Python-only: _MODULE_LANGUAGE_ADAPTERS has one entry (python) and _scan.py's symbol-move engine is Python AST-specific. Tracks widening to typescript/rust/c/cpp/kotlin/csharp/bash per T-2996's FACET_REFACTOR known-gap cells. strata is a design DSL without an established symbol-move convention; revisit if one emerges.