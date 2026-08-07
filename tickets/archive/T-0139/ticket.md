---
id: T-0139
title: editor syntax highlighting for .strata (VSCode + JetBrains via one TextMate
  grammar)
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- editors/**
- tests/unit/test_strata_tmlanguage.py
- docs/guides/editors.md
- docs/index.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_strata_tmlanguage.py::test_tmlanguage_is_valid_json
- tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
- tests/unit/test_strata_tmlanguage.py::test_string_pattern_terminates_at_end_of_line
designated_repro_test: null
threat: null
component: null
---
Build a single TextMate grammar (editors/vscode-strata/) covering .strata syntax, consumed directly by VSCode and via TextMate Bundles by JetBrains IDEs. Grammar must be drift-locked against strata-core/src/parse.rs's keyword dispatch via a bidirectional test. See docs/strata/surface.md for the grammar reference. Plan: (1) inventory the parser's construct/clause keywords, trust levels, delivery modes, literals, quantities, comments, arrow, delimiters; (2) editors/vscode-strata/package.json + language-configuration.json + syntaxes/strata.tmLanguage.json with anchored non-backtracking regexes; (3) editors/jetbrains/README.md documenting the TextMate Bundles route, no full IntelliJ plugin; (4) tests/unit/test_strata_tmlanguage.py: valid JSON, extracts parser keyword list, asserts bidirectional keyword parity, spot-checks quantity regex; (5) docs/guides/editors.md linked from docs/index.md. ASCII only, no emojis, no bare # TODO.