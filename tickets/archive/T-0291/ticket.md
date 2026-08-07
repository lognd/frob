---
id: T-0291
title: 'arch: gates+app long-function/god-class burndown to zero'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/app/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestSysGate::test_sys001_dangling
- tests/unit/test_check.py::TestCheckBuildsGraphOnce::test_run_check_calls_build_graph_exactly_once
- tests/system/test_cli_check.py::TestCheckSkipFlags::test_json_output
- tests/system/test_cli_check.py::TestCheckGatesStage::test_only_gates_passes_once_bound_and_tested
designated_repro_test: null
threat: null
component: null
---
## Description

`frob arch analyze .` (repo-wide) reported ~278 long-function (>threshold
lines, `frob.arch._python._check_long_functions`, default
`max_function_lines=30` -- frob.toml has no `[arch]` override) warnings
repo-wide. This ticket's slice: drive the long-function warnings in
`src/frob/gates/__init__.py` and `src/frob/app/**` to zero via genuine
extraction, without changing behavior or lowering the threshold.

## Plan

Filter `uv run frob arch .` output to the slice's two paths, extract one
cohesive private helper per over-long function (named for what it does),
re-run `frob arch .` after each file to confirm 0 remaining, keep the
touched-area pytest suites green throughout, then a final full
`uv run frob check` pass.