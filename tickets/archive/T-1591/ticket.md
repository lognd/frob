---
id: T-1591
title: 'suite: tests that pass in isolation but fail under xdist -- shared-state pollution'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/**
- src/frob/lang/**
- src/frob/serve/**
- src/frob/app/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_lang_strata.py::TestStrataNativeParserUnavailable::test_parse_file_returns_native_parser_unavailable
- tests/unit/test_lang_strata.py::TestStrataNativeParserUnavailable::test_outline_file_returns_err_not_crash
- tests/test_serve.py::TestCheckScope::test_in_scope_diff_passes
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
designated_repro_test: null
threat: null
component: null
---
A full 'pytest tests/' run reds ~8 tests that PASS when run in isolation with -p no:randomly, i.e. they depend on execution order or on state another test left behind in the same xdist worker. Confirmed members: tests/unit/test_lang_strata.py::TestStrataNativeParserUnavailable (2), tests/unit/test_app_runners.py::TestMapRunner/TestOutlineRunner (2), tests/test_lang.py::TestParseCache::test_second_call_same_content_is_a_hit, tests/test_serve.py::TestCheckScope::test_in_scope_diff_passes, tests/system/test_cli_perf.py::TestCheckOnlyPerf, tests/test_ticket_evidence.py::TestKindCliInvalidKind::test_invalid_kind_refused (AppConfig ValidationError instead of a clean refusal), tests/test_coverage.py::TestCoverageTargetNativesGuard, tests/test_ticket_land.py::TestClaimDivergencePostMerge.

This is the most corrosive failure class we have: it makes the suite's verdict depend on worker assignment, so a red run gets dismissed as 'flaky' and real regressions hide behind it (this drive already had 'gates green is not suite green' bite twice).

Per test: reproduce with the same seed/worker ordering (pytest -p no:randomly with the failing test AFTER its polluter, or -p xdist with -n matching), find the shared mutable state (module-level caches like frob.lang's parse memo, monkeypatched globals, cwd, env vars, .frob/ derived state), and fix it at the source with an autouse reset fixture rather than reordering tests. tests/conftest.py already has this shape for the parse cache (T-0926) and color env (T-1586).