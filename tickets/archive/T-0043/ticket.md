---
id: T-0043
title: Migrate arch + dup/_legacy off frob.ast, then delete frob.ast
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/dup/**
- src/frob/ast/**
- src/frob/lang/**
- tests/unit/test_lang_primitives.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_lang_primitives.py::test_child_by_field_and_node_text_public_wrappers
- tests/test_lang.py::test_lang_pipeline_integration
- tests/unit/test_arch.py::test_arch_end_to_end_analyze_then_render
- tests/unit/test_dup.py::test_dup_end_to_end_scan_then_render
designated_repro_test: null
threat: null
component: null
---
Re-platform left two frob.ast consumers needing raw node traversal
not yet in frob.lang: arch (child_by_field/text, 10 sites) and
dup/_legacy (14 sites). Add the needed traversal primitives to frob.lang,
migrate both, then delete src/frob/ast.