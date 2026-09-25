---
id: T-6513
title: wire frob ci report into _root.py's parser tree (register _add_ci_parser)
state: queued
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/_cli_parsers/_root.py
- src/frob/_cli_parsers/__init__.py
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-draft-c099f096 (CI-1) built _cli_parsers/_ci.py, app/ci_runner.py, config.py Subcommand.ci/ci_* fields, and app.py's runner mapping, all tested directly (tests/unit/cli/test_ci_report.py, 4/4 green). The final registration step -- exporting _add_ci_parser from _cli_parsers/__init__.py and calling it in _root.py's _add_workflow_subparsers (mirrors _add_verify_parser) -- was blocked the whole session by T-draft-4ad886c1 (COORD-1)'s live exclusive lease on those same two files. Do this once COORD-1 lands/merges: add _add_ci_parser to _cli_parsers/__init__.py's re-export list and call it in _root.py next to _add_verify_parser(sub).