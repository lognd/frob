---
id: T-1320
title: Re-baseline TEST005 for src/frob/app before continuing T-1276
state: done
kind: docs
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:uv run --frozen frob check --only test exit=0 sha256=5383529021de
designated_repro_test: null
acceptance:
- text: GIVEN main's HEAD WHEN make coverage + frob check --stamp-coverage runs THEN
    the TEST005 finding list for src/frob/app is re-derived and T-1276 is re-scoped
    or closed accordingly
  evidence:
  - cmd:uv run --frozen frob check --only test exit=0 sha256=5383529021de
threat: null
component: null
---
T-1276's baseline (115 TEST005 findings, 63 at exactly 0.0% branch) is a
stale coordinator-side coverage-stamp snapshot. A T-1276 attempt sampled
17 of the 63 listed 0.0%-branch symbols across 15 files via targeted
pytest --cov runs against each symbol's own dedicated test file (not the
full suite) and every one already showed 68-100% real branch coverage
from existing, already-landed tests -- fleet_runner::run,
gitlog_runner::run, arch_runner::run, vet_runner::run, dup_runner::run,
natives_runner::run, deploy_runner::run, parse_runner::run,
agent_runner, clean_runner, debt_runner, deprecated_runner, fmt_runner,
pool_runner, worktree_runner, and all 9 telemetry.py functions.

A sub-agent cannot regenerate a trustworthy full-suite coverage stamp
itself (playbook agent-playbook.md#6b is coordinator-only, and this was
confirmed empirically in the T-1276 attempt: a pytest --cov run scoped to
just the app package's own test files still SIGTERMed past a 540s
foreground timeout without finishing).

Work: coordinator runs `make coverage` + `frob check --stamp-coverage`
against current main, re-derives the real TEST005 finding list for
src/frob/app/**, and either re-scopes T-1276 (if requeued) with the
current list, or closes it outright if the list is now empty.