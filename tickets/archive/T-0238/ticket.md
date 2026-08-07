---
id: T-0238
title: frob outline has no Rust adapter though frob.lang parses Rust
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/outline/**
- tests/**
- docs/commands/outline.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_outline.py::test_rust_outline_ok
- tests/unit/test_outline.py::test_rust_outline_functions
- tests/unit/test_outline.py::test_rust_outline_classes
- tests/unit/test_outline.py::test_rust_outline_methods
- tests/unit/test_outline.py::test_rust_outline_as_text
designated_repro_test: null
threat: null
component: null
---
Found while writing T-0159's extending guides: 'frob outline strata-core/src/parse.rs' errors with 'No outline adapter for this file extension' even though frob.lang extracts 151 symbols from the same file (dispatching path=strata-core/src/parse.rs to grammar=rust). The outline adapter registry does not cover every language frob.lang supports; either add the missing adapters (rust at minimum, check c/cpp/tsx too) or have outline fall back to the frob.lang symbol walk so the two language registries cannot drift apart. (Refiled: first draft was lost in a tickets.md ledger splice during T-0159's concurrent-agent merge.)