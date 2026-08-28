---
id: T-3232
title: frob.docs/frob.xref narrower per-language coverage than frob.lang
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/docs/**
- src/frob/xref/**
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
T-2996's unfaceted_packages AST detection cross-check found frob.docs.__init__ filters docstring extraction to language=='python' only (skips every other language's docstrings), and frob.xref.__init__._LANG_EXTS only maps python/c/cpp/strata (missing typescript/rust/kotlin/csharp/bash) for its --lang filter, both narrower than frob.lang.supported_languages(). Measured, not fixed, in T-2996's scope (frob.lang's facet registry, not these packages' implementations).