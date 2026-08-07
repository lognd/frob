---
id: T-0580
title: 'command-tier audit: demote or deprecate the navigation porcelain (map/outline/xref/docs)
  -- zero organic use'
state: done
kind: ux
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/map_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/xref_runner.py
- src/frob/app/docs_runner.py
- src/frob/__main__.py
- docs/modules/cli.md
- docs/index.md
- tests/system/test_cli_map.py
- tests/system/test_cli_outline.py
- tests/system/test_cli_xref.py
- tests/unit/test_app_runners.py
- tests/unit/test_app_runners_batch5.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/map_runner.py
  reason: 'user decision 2026-07-23: deprecate map/outline/xref/docs-search with pre-1.0.0
    sunset; scope covers the four runners, the parser layer for deprecation warnings,
    and CLI docs'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/outline_runner.py
  reason: 'user decision 2026-07-23: deprecate map/outline/xref/docs-search with pre-1.0.0
    sunset; scope covers the four runners, the parser layer for deprecation warnings,
    and CLI docs'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/xref_runner.py
  reason: 'user decision 2026-07-23: deprecate map/outline/xref/docs-search with pre-1.0.0
    sunset; scope covers the four runners, the parser layer for deprecation warnings,
    and CLI docs'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/docs_runner.py
  reason: 'user decision 2026-07-23: deprecate map/outline/xref/docs-search with pre-1.0.0
    sunset; scope covers the four runners, the parser layer for deprecation warnings,
    and CLI docs'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/__main__.py
  reason: 'user decision 2026-07-23: deprecate map/outline/xref/docs-search with pre-1.0.0
    sunset; scope covers the four runners, the parser layer for deprecation warnings,
    and CLI docs'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/cli.md
  reason: 'user decision 2026-07-23: deprecate map/outline/xref/docs-search with pre-1.0.0
    sunset; scope covers the four runners, the parser layer for deprecation warnings,
    and CLI docs'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/index.md
  reason: DOC001 requires the new docs/modules/cli.md page be linked from somewhere;
    docs/index.md is the module index every other docs/modules/*.md page is linked
    from
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/system/test_cli_map.py
  reason: 'covers_scope route 2: these files contain the 7 functional evidence tests
    proving the four deprecated runners still work with the warning in place; scope
    originally listed only runner+doc files so D-02 could not bind'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/system/test_cli_outline.py
  reason: 'covers_scope route 2: these files contain the 7 functional evidence tests
    proving the four deprecated runners still work with the warning in place; scope
    originally listed only runner+doc files so D-02 could not bind'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/system/test_cli_xref.py
  reason: 'covers_scope route 2: these files contain the 7 functional evidence tests
    proving the four deprecated runners still work with the warning in place; scope
    originally listed only runner+doc files so D-02 could not bind'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_app_runners.py
  reason: 'covers_scope route 2: these files contain the 7 functional evidence tests
    proving the four deprecated runners still work with the warning in place; scope
    originally listed only runner+doc files so D-02 could not bind'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_app_runners_batch5.py
  reason: 'covers_scope route 2: these files contain the 7 functional evidence tests
    proving the four deprecated runners still work with the warning in place; scope
    originally listed only runner+doc files so D-02 could not bind'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/system/test_cli_map.py::test_exit_code_zero
- tests/system/test_cli_outline.py::test_exit_code_zero_on_valid_python
- tests/system/test_cli_xref.py::test_exit_zero_found_symbol
- tests/unit/test_app_runners.py::TestMapRunner::test_text_mode_logs_summary
- tests/unit/test_app_runners.py::TestXrefRunner::test_missing_symbol_exits_1
- tests/unit/test_app_runners.py::TestOutlineRunner::test_directory_target_falls_back_to_map
- tests/unit/test_app_runners_batch5.py::TestDocsRunner::test_search_finds_match_text_mode
designated_repro_test: null
threat: null
component: null
---
Telemetry (this session, 1035 CLI events): ticket=225 check=103 release=19 sys=16 organic; map/outline/xref/parse/gitlog/exports invocations were VIRTUALLY ALL their own test suites (pytest tmp paths), zero organic use by coordinator or ~30 agents -- navigation is owned by Serena/native tools in agentic use. Each command carries doc/test/export/coverage obligations = maintenance tax. Decide per command: KEEP AS PLUMBING (parse: adapter used by pipelines; exports: powers exports stage; gitlog: powers stats/changelog), DEMOTE to documented maintenance-mode porcelain tier (map, outline, xref, docs-search), or frob:deprecated. serve (MCP) kept: valuable for no-shell contexts though unused when agents have a shell. User decision ticket -- evidence in body, recommendation: demote the four navigation commands, revisit removal after one quiet quarter.