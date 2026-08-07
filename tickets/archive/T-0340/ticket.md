---
id: T-0340
title: native extensions get uninstalled by uv sync/build -- make strata_core/frob_core
  survive (or auto-rebuild)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- pyproject.toml
- docs/**
- tickets.md
- tests/integration/test_interfaces.py
- tests/system/test_cli_doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/integration/test_interfaces.py
  reason: 'Makefile/docs-only ticket: evidence is the sanctioned pre-existing CLI-dispatch
    + doctor natives tests (playbook section 5); close requires them in scope'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: 'Makefile/docs-only ticket: evidence is the sanctioned pre-existing CLI-dispatch
    + doctor natives tests (playbook section 5); close requires them in scope'
  actor: logan
  at: '2026-07-22'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_reports_healthy_when_natives_present
designated_repro_test: null
acceptance:
- text: given the editable maturin-develop natives (strata_core, frob_core) are built,
    when any uv operation that re-syncs the environment runs (uv lock, uv sync, uv
    build via frob release stamp, or a uv run that triggers a sync after a pyproject
    change), then the natives remain importable -- either uv is configured not to
    evict them, or they are transparently rebuilt, so pytest collection / frob check
    never silently degrade to NativeExtensionUnavailable mid-run
  evidence: []
- text: given a fresh clone or a stamp that did evict them, when the developer/agent
    runs the standard build/test entrypoint, then natives are ensured present with
    no manual 'make core' needed as a separate remembered step
  evidence: []
threat: null
component: null
---
Recurring, high-cost friction ([[worktree-natives-artifact]]): the maturin-develop editable installs of strata_core/frob_core are not tracked in uv.lock, so uv treats them as extras and REMOVES them on any environment re-sync -- triggered by , , load_graph: loaded 6496 symbols, 4043 edges
release: stamped 927 public symbol(s) at 0.20.0
stamped public API at 0.20.0 -> .frob-release.json's build step, or a Provide a command or script to invoke with `uv run <command>` or `uv run <script>.py`.

The following commands are available in the environment:

- cffi-gen-src
- coverage
- coverage-3.11
- coverage3
- dotenv
- frob
- httpx
- hypothesis
- idna
- jsonschema
- mcp
- py.test
- pygmentize
- pytest
- python
- python3
- python3.11
- ruff
- ty
- uvicorn

See `uv run --help` for more information. after a pyproject edit. This bit the campaign live multiple times (a black-dep edit and every version-bump stamp nuked them mid-flow, causing SYS004/collection failures that look like regressions). Options to evaluate: (a) a  setting /  sync mode that stops uv evicting them; (b) a Makefile/entrypoint wrapper (e.g. a  target or a post-sync hook) that rebuilds natives whenever they're missing before test/check; (c) building+installing them as real (non-editable) wheels pinned in the lock. Pick the one that makes 'natives are always present' an invariant, not a remembered manual step. This is the deepest papercut behind the whole worktree-natives artifact class.