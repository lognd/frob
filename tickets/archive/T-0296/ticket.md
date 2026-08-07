---
id: T-0296
title: 'arch: core-commands long-function burndown to zero'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/tickets/**
- src/frob/check/**
- src/frob/__main__.py
- src/frob/deploy/**
- src/frob/fuzz/**
- src/frob/lang/**
- src/frob/testing/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/test_vet.py::TestAllowConfig::test_no_frob_toml_is_advisory_only
- tests/test_tickets.py::TestArchive::test_blocked_by_archived_ticket_resolves_closed
- tests/unit/test_check.py::TestCheckBuildsGraphOnce::test_run_check_calls_build_graph_exactly_once
- tests/unit/deploy/test_audit.py::TestAttest::test_all_green
- tests/test_testing.py::TestCargoEnv::test_cargo_env_err_when_no_qualifying_interpreter
- tests/test_lang.py::TestErrors::test_supported_languages
- tests/test_fuzz.py::TestFuzz001::test_flags_obligated_symbol_with_no_fuzz_test
designated_repro_test: null
threat: null
component: null
---
## Description

`frob arch .` reported ~70 long-function (>threshold lines,
`frob.arch._python._check_long_functions`, default
`max_function_lines=30`) warnings across
`src/frob/vet/**`, `src/frob/tickets/**`, `src/frob/check/**`,
`src/frob/__main__.py`, `src/frob/deploy/**`, `src/frob/fuzz/**`,
`src/frob/lang/**`, `src/frob/testing/**`. This ticket's slice: drive
those to zero via behavior-preserving extraction, no threshold or config
changes, no public API change.

## Plan

Filter `uv run frob arch .` to the scoped subtrees, extract cohesive
private helpers per over-long function (or, where the function was long
only because of an oversized rationale docstring, move that prose to a
leading comment above the def), re-run `frob arch .` after each pass to
converge on 0 in every subtree, keep the touched-area pytest suites
green, then a final full `uv run frob check` after `make coverage`.