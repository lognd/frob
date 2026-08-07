---
id: T-1237
title: 'coverage forensics: persist failure list before frob clean destroys it'
state: done
kind: bug
origin: agent
created: '2026-07-29'
priority: high
parent: T-0969
tier: ticket
sprint: null
scope:
- Makefile
- src/frob/clean/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_clean.py::test_safe_tier_clean_preserves_frob_junitxml_forensics
- tests/test_clean.py::test_makefile_coverage_recipe_never_escalates_clean_tier
designated_repro_test: null
acceptance:
- text: GIVEN a make coverage run with failures THEN the failing test ids survive
    the recipe (junitxml or equivalent persisted under .frob/ before frob clean -y)
    and the clean tier rules never delete mid-run .coverage.* fragments (investigate
    the observed 34->27 fragment loss)
  evidence:
  - tests/test_clean.py::test_safe_tier_clean_preserves_frob_junitxml_forensics
  - tests/test_clean.py::test_makefile_coverage_recipe_never_escalates_clean_tier
threat: null
component: null
---
T-0969 diagnosis: the recipe's trailing frob clean -y deletes .pytest_cache (clean/_rules.py:30) destroying --last-failed evidence, and tier-1 .coverage.* rule (rule line 27) may nuke mid-run fragments -- one subset run ended with 27 data files where a single test file generates 34, unresolved.