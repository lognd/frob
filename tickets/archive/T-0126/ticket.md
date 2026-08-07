---
id: T-0126
title: annotate newly-extracted module constants with frob:doc edges (COV001 x21)
state: done
kind: docs
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/**
- scripts/**
- docs/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_lang.py::TestParsePython::test_module_level_literal_const_extracted
- tests/test_lang.py::TestParsePython::test_module_level_call_expression_const_extracted
designated_repro_test: null
threat: null
component: null
---
T-0087 fixed CONST extraction (module-level assignments were invisible to the graph). The fix's fallout was deferred until the global tool reinstall: 21 public module-level constants across src/ and scripts/ (e.g. scripts/bump_version.py::PYPROJECT, strata TRUST/LABELS) now correctly surface as public symbols with no frob:doc edge, failing COV001 at error severity. Add frob:doc edges pointing at the owning module's docs page (add a constants section where none exists), or prefix genuinely-internal constants with an underscore where privacy is the honest fix. No threshold or severity changes.