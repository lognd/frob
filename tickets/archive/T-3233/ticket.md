---
id: T-3233
title: frob._cli_parsers --lang choices drifted narrower than frob.lang
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: v1.1.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_check.py
- src/frob/_cli_parsers/_core.py
- docs/commands/check.md
- tests/unit/test_cli_lang_choices_drift.py
- docs/commands/xref.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: narrow off src/frob/_cli_parsers/_ticket/_closeout_evidence.py, leased by
    T-4550; actual --lang choices drift is in _check.py and _core.py only (reads frob.lang
    read-only, no write scope needed there)
  actor: logan
  at: '2026-09-18'
- op: add
  glob: src/frob/_cli_parsers/_check.py
  reason: narrow off src/frob/_cli_parsers/_ticket/_closeout_evidence.py, leased by
    T-4550; actual --lang choices drift is in _check.py and _core.py only (reads frob.lang
    read-only, no write scope needed there)
  actor: logan
  at: '2026-09-18'
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: narrow off src/frob/_cli_parsers/_ticket/_closeout_evidence.py, leased by
    T-4550; actual --lang choices drift is in _check.py and _core.py only (reads frob.lang
    read-only, no write scope needed there)
  actor: logan
  at: '2026-09-18'
- op: add
  glob: docs/commands/check.md
  reason: 'close scope-closure warning: _add_check_parser''s frob:doc target'
  actor: logan
  at: '2026-09-18'
- op: add
  glob: tests/unit/test_cli_lang_choices_drift.py
  reason: new drift-lock test for the shared _LANG_CHOICES derivation
  actor: logan
  at: '2026-09-18'
- op: add
  glob: docs/commands/xref.md
  reason: 'close scope-closure warning: _LANG_CHOICES''s frob:doc target'
  actor: logan
  at: '2026-09-18'
evidence:
- tests/unit/test_cli_lang_choices_drift.py::TestLangChoicesDeriveFromFrobLangRegistry::test_lang_choices_track_frob_lang_registry
- tests/unit/test_cli_lang_choices_drift.py::TestLangChoicesDeriveFromFrobLangRegistry::test_cycle_lang_choices_match_registry
- tests/unit/test_cli_lang_choices_drift.py::TestLangChoicesDeriveFromFrobLangRegistry::test_xref_lang_choices_match_registry
- tests/unit/test_cli_lang_choices_drift.py::TestLangChoicesDeriveFromFrobLangRegistry::test_exports_lang_choices_match_registry
- tests/unit/test_cli_lang_choices_drift.py::TestLangChoicesDeriveFromFrobLangRegistry::test_all_three_lang_flags_share_the_identical_choices_object
designated_repro_test: null
acceptance:
- text: GIVEN frob cycle/xref/exports --consumers's --lang flags WHEN frob.lang gains
    or loses a tree-sitter grammar THEN all three flags' choices update automatically
    from one shared, frob.lang-derived source instead of three separately hand-typed
    literals
  evidence:
  - tests/unit/test_cli_lang_choices_drift.py::TestLangChoicesDeriveFromFrobLangRegistry::test_lang_choices_track_frob_lang_registry
  - tests/unit/test_cli_lang_choices_drift.py::TestLangChoicesDeriveFromFrobLangRegistry::test_cycle_lang_choices_match_registry
  - tests/unit/test_cli_lang_choices_drift.py::TestLangChoicesDeriveFromFrobLangRegistry::test_xref_lang_choices_match_registry
  - tests/unit/test_cli_lang_choices_drift.py::TestLangChoicesDeriveFromFrobLangRegistry::test_exports_lang_choices_match_registry
  - tests/unit/test_cli_lang_choices_drift.py::TestLangChoicesDeriveFromFrobLangRegistry::test_all_three_lang_flags_share_the_identical_choices_object
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2996 measured several --lang argparse choices lists (xref, cycle, check) hard-coded to ['python','cpp','c'], narrower than frob.lang.supported_languages() (9 languages). Measured, not fixed, in T-2996's scope.