---
id: T-0091
title: make core creates a stray venv under strata-core/, contaminating the editable
  install
state: done
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- Makefile
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_crash.py::TestEvaluateCrashContractsNoContracts::test_empty_report_when_no_node_declares_a_crash_contract
- tests/unit/strata/test_crash.py::TestNoHangCheck::test_timeout_shorter_than_restart_bound_fails_closed
designated_repro_test: null
threat: null
component: null
---
found while working T-0062: running `make core` from repo root invokes `cd strata-core && uvx maturin develop --uv --release`, which (unlike the frob-core target) causes uv/maturin to create and install into a fresh strata-core/.venv instead of the repo root .venv, so the root .venv's installed strata_core.abi3.so goes stale after a rebuild until VIRTUAL_ENV is pinned manually. Repro: rm -rf strata-core/.venv; make core; compare md5sum of strata-core/target/release/libstrata_core.so vs .venv/lib/python3.11/site-packages/strata_core/strata_core.abi3.so -- they differ. Workaround used in T-0062: VIRTUAL_ENV=$(pwd)/.venv uvx maturin develop --uv --release -m strata-core/Cargo.toml. Suggested fix: set VIRTUAL_ENV explicitly in the Makefile core target for both crates, or add a .python-version/uv marker to strata-core/ so uv resolves the root venv the same way it does for frob-core.