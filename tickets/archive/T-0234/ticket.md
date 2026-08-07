---
id: T-0234
title: generated-file marker respected by coverage gates (COV001 on generated sources)
state: done
kind: ux
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- docs/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_detects_repo_convention_header
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_detects_do_not_edit_and_at_markers
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_false_for_hand_authored_file
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_false_for_missing_file
- tests/test_gates.py::TestCoverageGate::test_cov001_exempts_generated_file_with_marker
- tests/test_gates.py::TestCoverageGate::test_cov001_still_fires_without_generated_marker
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 23: graphite frontend/src/api/api.generated.ts draws COV001 doc-edge demands (its repo ticket T-0006 documents the dead end). The [graph] excludes leaf exists but repos want generated code IN the graph (xref) yet exempt from doc/test obligations. Add a generated marker (glob list in frob.toml, or filename pattern *.generated.*) that COV/TEST gates respect while graph/xref still see the symbols.