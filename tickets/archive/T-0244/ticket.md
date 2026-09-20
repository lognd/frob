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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/**
- src/frob/strata/**
- src/frob/lang/**
- docs/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_core.py'
  actor: logan
  at: '2026-09-19'
  old_length: 539
  new_length: 1725
evidence:
- tests/vet_suite/test_capability_scan_embedded.py::TestEmbeddedCodeCapability::test_embedded_html_script_string_detected
- tests/vet_suite/test_capability_scan_embedded.py::TestEmbeddedCodeCapability::test_embedded_code_region_below_size_threshold_not_detected
- tests/vet_suite/test_capability_scan_embedded.py::TestEmbeddedCodeCapability::test_embedded_code_declared_even_when_content_opaque_to_needles
- tests/vet_suite/test_capability_scan_embedded.py::TestEmbeddedCodeCapability::test_embedded_code_regions_scanned_via_operations
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (design-level): the product dashboard is 5400 lines of inline HTML/JS inside a python module -- invisible to capability scanning even post-T-0169. Options to evaluate honestly: (a) detect large embedded html/script string literals and run the TS/JS needle pass over their content; (b) an explicit OutOfScope/managed-style marker declaring embedded-frontend content with a reason, so the blind spot is at least DECLARED not silent. Start with (b) (cheap, honest), spike (a).

T-4718 sweep (condensed from src/frob/vet/_capability_core.py, the
embedded-code blind spot block, trimmed for DOCARCH002's 12-line cap):
the trimmed block's full original text, kept verbatim below.

# T-0244: embedded-code blind spot. Every needle table above only ever
# scans a file's OWN source-grammar text; a large HTML/JS-shaped STRING
# LITERAL sitting inside a Python module (the malmberg pilot P3 shape -- a
# 5400-line dashboard's markup/script embedded as a python string) is
# structurally invisible to it. The functions below detect such a region
# (a size + HTML/JS-signal heuristic over python tree-sitter `string`
# nodes) and ALWAYS emit the `embedded_code` capability kind for a region
# found, independent of whether the best-effort typescript-needle re-scan
# over the region's own text turns up anything specific -- fail-closed per
# docs/design/structural-linter-adversarial-hardening.md rule 3: the
# region is declared, never silently passed, even when the re-scan is
# empty. Python only for this pass (the ticket's own reported shape);
# extending detection to other host languages embedding HTML/JS strings is
# a documented follow-up, not attempted here.