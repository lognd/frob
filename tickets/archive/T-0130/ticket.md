---
id: T-0130
title: 'design/litmus strata symbols: exclude from doc/test obligations'
state: done
kind: docs
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- frob.toml
- tickets.md
- tests/test_excludes.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_excludes.py::test_repo_excludes_litmus_strata_from_obligation_surface
- tests/test_excludes.py::test_load_and_match_globs
- tests/test_excludes.py::test_dup_scanner_honors_exclude
designated_repro_test: null
threat: null
component: null
---
T-0129 wired .strata into frob.graph's source-extension scan (frob.lang.supported_extensions()), so design/litmus/*.strata symbols are now real graph nodes. frob check now reports ~93 COV001 (no frob:doc edge) and matching TEST001 violations for every public strata construct in chirp.strata/payments.strata/payments_hardened.strata/tube.strata -- these are litmus test fixtures (analogous to tests/fixtures/**, which IS excluded via frob.toml's [scan] exclude), not maintained application code. Either exclude design/litmus/** from graph/gates coverage obligations the same way tests/fixtures/** is excluded, or add frob:doc/frob:tests anchors to the litmus files if they are meant to carry real documentation. Filed instead of touched directly: frob.toml and design/litmus content are outside T-0129's declared scope (src/frob/graph/**, outline/**, xref/**, testing/**, policy/**, app/cycle_runner.py, arch/__init__.py).