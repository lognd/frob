---
id: T-3597
title: Windows CI diagnostic step resolves fixture project instead of frob checkout
  (ModuleNotFoundError)
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- scripts/frob_check_diag.py
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
run 33412543005, HEAD 2bb9c46ea: T-3589's Windows diagnostic step does Push-Location $fixture then uv run python $RUNNER_TEMP/frob_check_diag.py -- uv resolves the FIXTURE directory's project env from that cwd and the child dies with ModuleNotFoundError: No module named 'frob' before the watchdog ever runs, voiding the whole measurement. Fix ci.yml: run uv run --project D:\a\frob\frob python ... (or stay in the repo root and pass the fixture path as the frob check <path> argument -- the diag script hardcodes sys.argv=["frob","check","--budget","180"], so also make it check the fixture path explicitly). This gates the entire Windows CI thread.