---
id: T-0159
title: 'extending frob: developer guides for every registry and extension point'
state: done
kind: docs
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0153
- T-0154
- T-0155
- T-0157
- T-0158
parent: null
tier: ticket
sprint: null
scope:
- docs/guides/**
- docs/index.md
- src/frob/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_row_has_a_guide_file
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_row_anchor_file_exists_and_mentions_guide
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_anchor_fragment_resolves_to_guide_h1
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_no_orphan_guides
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_probe_table_and_inventory_agree
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_probe_still_matches_source
designated_repro_test: null
threat: null
component: null
---
A guide series under docs/guides/extending/ making every registry trivially extendable. INVENTORY FIRST: enumerate every registry/extension point in the codebase -- at minimum: gate rule families and their registration (COV/TEST/DRIFT/SCOPE/PRE/DOC/PERF/SYS/THREAT/COMPLIANCE/WAIVE), comment DSL directives (frob:ticket/tests/doc/waive/todo/invariant/channel/boundary/secret), threat catalog (WeaknessEntry/OutOfScopeEntry/views incl. the separate-views precedent), compliance regulations/views, capability registry + pattern tables + per-language matrix cells (T-0158), CVE fingerprints (T-0153), PII categories (T-0154), design-lint rules (T-0155), secrets-scan providers (T-0157), prover claim kinds, scenario kinds, strata surface grammar keywords (and the tmLanguage drift-lock), [[test.runner]] entries, language grammar handlers, sys export formats, litmus fixture mappings, benign capabilities, ticket kinds/states. ONE GUIDE PER REGISTRY on a common template: what it is and where it lives (file paths + symbol names); step-by-step 'add a new entry' recipe; WHICH DRIFT-LOCKS WILL FIRE when you add one and exactly what each demands (fixture, test, excuse entry, doc anchor, golden regen); a worked example diff; common mistakes (cite real session incidents where instructive, e.g. separate-views vs widening defaults, self-match false positives, stale-comment traps). ANTI-ROT MECHANISM (the point of doing this in frob): every guide is bound to its registry's code symbol with frob:doc anchors so the DOC gates flag drift when the registry changes; plus a completeness drift-lock test -- a machine-readable registry-of-registries (the inventory above) asserting every entry has a guide file and a live anchor, so ADDING A NEW REGISTRY without a guide fails the build. docs/index.md gains an Extending section linking every guide. Writing guides will require reading each registry's code carefully -- fix nothing beyond doc anchors; file tickets for any defect discovered while documenting.