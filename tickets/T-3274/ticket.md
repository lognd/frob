---
id: T-3274
title: Extend T-3192 hang-guard positive control to macOS/Windows CI steps
state: queued
kind: docs
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_ci_hang_guard_positive_control.py
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
T-3250 added step-level stack-dump-on-hang guards for macOS (bash kill -ABRT) and a timed-failure guard for Windows (pwsh Wait-Process/Stop-Process) in .github/workflows/ci.yml, mirroring ubuntu's timeout -s ABRT step. The existing positive control (tests/system/test_ci_hang_guard_positive_control.py) only proves the Linux mechanism (skipif win32) and only exercises the GNU timeout + PYTHONFAULTHANDLER recipe, not the new shell-builtin kill -ABRT loop or the pwsh Wait-Process/Stop-Process guard. Extend that pattern (a real planted-hang subprocess run, not a YAML/mock assertion) to cover the macOS kill -ABRT path and, separately, the Windows timed-failure path (documenting that Windows gets no stack dump by PLATFORM001 declared boundary). Out of scope for T-3250 because that ticket's scope is limited to .github/workflows/ci.yml only.