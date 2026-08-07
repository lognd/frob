---
id: T-0554
title: 'check: doc/coverage/drift/inv gates run ONLY in the Python pipeline (T-0404
  finding 1)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: high
parent: T-0404
tier: ticket
sprint: null
scope:
- src/frob/check/
- tests/unit/test_check.py
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check.py
  reason: T-0554 needs unit tests proving the gates stage now runs in the cpp/rust/ts
    pipelines (tests/unit/test_check.py); no new production module to add to scope
  actor: logan
  at: '2026-07-22'
- op: add
  glob: pyproject.toml
  reason: T-0554's public-API signature changes (new kwargs on run_check_cpp/rust/ts)
    trip REL001 major-bump; version bump + frob release stamp touch pyproject.toml/.frob-release.json,
    and uv sync after the bump touches uv.lock's project version metadata
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: T-0554's public-API signature changes (new kwargs on run_check_cpp/rust/ts)
    trip REL001 major-bump; version bump + frob release stamp touch pyproject.toml/.frob-release.json,
    and uv sync after the bump touches uv.lock's project version metadata
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: T-0554's public-API signature changes (new kwargs on run_check_cpp/rust/ts)
    trip REL001 major-bump; version bump + frob release stamp touch pyproject.toml/.frob-release.json,
    and uv sync after the bump touches uv.lock's project version metadata
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_check.py::TestRunCheckCpp::test_gates_stage_runs_by_default
- tests/unit/test_check.py::TestRunCheckRust::test_gates_stage_runs_by_default
- tests/unit/test_check.py::TestRunCheckTs::test_gates_stage_runs_by_default
designated_repro_test: null
threat: null
component: null
---
docs/audits/lang-check-docs.md finding 1. run_check_cpp/run_check_rust/run_check_ts never call _run_gates -- only _python_tasks does. A pure Rust/C++/TS repo runs its native toolchain only; COV001/DOC001/DOC002/DOC003/DRIFT001/DRIFT002/INV/DEC/TODO001 never execute despite the polyglot doc-binding promise (lang/__init__.py module docstring). Repro: a repo with only package.json, add a public exported symbol and a lying/broken frob:doc -> frob check green. RIGHT-WAY fix: run the gates stage in every pipeline (build the graph once, run run_gates regardless of detected language), or at minimum emit a loud gates-NOT-run-for-<lang> stage line. Large, cross-cutting dispatch change -- too large for the T-0404 sweep budget.