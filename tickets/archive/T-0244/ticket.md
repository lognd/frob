---
id: T-0244
title: 'embedded-code blind spot: JS/HTML inside python string literals invisible
  to every scanner'
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/strata/**
- src/frob/lang/**
- docs/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestEmbeddedCodeCapability::test_embedded_html_script_string_detected
- tests/test_vet.py::TestEmbeddedCodeCapability::test_embedded_code_region_below_size_threshold_not_detected
- tests/test_vet.py::TestEmbeddedCodeCapability::test_embedded_code_declared_even_when_content_opaque_to_needles
- tests/test_vet.py::TestEmbeddedCodeCapability::test_embedded_code_regions_scanned_via_operations
designated_repro_test: null
threat: null
component: null
---
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (design-level): the product dashboard is 5400 lines of inline HTML/JS inside a python module -- invisible to capability scanning even post-T-0169. Options to evaluate honestly: (a) detect large embedded html/script string literals and run the TS/JS needle pass over their content; (b) an explicit OutOfScope/managed-style marker declaring embedded-frontend content with a reason, so the blind spot is at least DECLARED not silent. Start with (b) (cheap, honest), spike (a).