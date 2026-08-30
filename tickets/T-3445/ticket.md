---
id: T-3445
title: strata tmLanguage grammar missing V-model keywords (architecture, configuration,
  entity, code_ref, obligation, runnable)
state: done
kind: bug
origin: agent
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- editors/**
- tests/unit/test_strata_tmlanguage.py
- src/frob/deploy/_drift.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33282540898 (ubuntu-latest, HEAD b94cea5d0, 2026-08-30) -- the first run that completed to 100% (20 failures of 12689). This failure is in the cross-platform set (fails on macOS too unless noted). Reproduce locally by node id with -p no:xdist first; if it passes locally, the defect is an environment dependency (git identity, tmp path shape, missing tool, timing) and the fix must make the test hermetic, not skip it.

FAILING (2): tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally
    parser construct keywords missing from tmLanguage declaration-keywords: [architecture, configuration, entity]
  tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
    parser clause keywords missing from tmLanguage clause-keywords: [architecture, code_ref, entity, obligation, runnable]
The strata parser (strata-core) gained V-model constructs/clauses (T-3044/T-3260) that the editor tmLanguage grammar under editors/ was never updated for. Add the keywords to the tmLanguage (and any JetBrains mirror the README documents), keep the bidirectional test as the guard.