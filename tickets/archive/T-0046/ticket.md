---
id: T-0046
title: 'Refactor: clear perf/arch/test warnings in app,process,serve,testing,map,outline,xref,cycle,gitlog,policy'
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
- src/frob/process/**
- src/frob/serve/**
- src/frob/testing/**
- src/frob/map/**
- src/frob/outline/**
- src/frob/xref/**
- src/frob/cycle/**
- src/frob/gitlog/**
- src/frob/policy/**
- src/frob/__main__.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_gitlog.py::test_git_log
- tests/unit/test_cycle.py::test_simple_cycle
- tests/system/test_cli_cycle.py::test_no_cycle_exit_zero
- tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero
- tests/system/test_cli_map.py::test_exit_code_zero
- tests/test_testing.py::TestSelect::test_direct_hit
- tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
- tests/unit/test_app.py::test_config_no_subcommand
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_new_list_doable
- tests/system/test_cli_graph.py::TestGraphBuild::test_build_reports_stats
- tests/test_policy.py::TestRules::test_forbidden_import_fires
- tests/unit/test_outline.py::test_py_outline_methods
- tests/system/test_cli_outline.py::test_json_myclass_has_methods
- tests/test_testing.py::TestCollectPythonTests::test_parses_node_ids_and_caches_on_content_hash
- tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero
- tests/unit/test_ts_parsers.py::TestParseEslint::test_errors_and_warnings
designated_repro_test: null
threat: null
component: null
---
Refactor campaign: extract cohesive helpers across the app/process/serve/testing/command modules so no function trips PERF00x or the long-function bar, preserving behavior. Accounts for the touched-set under frob check COV002.