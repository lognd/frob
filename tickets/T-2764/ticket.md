---
id: T-2764
title: frob check does not run check_native_staleness_or_exit; make check does (workflow-parity
  gap)
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/**
- src/frob/check.py
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
Found while working T-2245 (docs-only scope, could not fix in place).
`make check`'s recipe runs `check_native_staleness_or_exit`
(src/frob/strata/_native_staleness.py) BEFORE `uv run frob check` --
confirmed via `frob explore xref check_native_staleness_or_exit`: its only
non-test caller is the Makefile's `check:` target and design/frob.strata's
declaration, nothing in src/frob/_cli_parsers or the frob check entrypoint
itself. This means an agent running `uv run frob check` directly (the
T-1382-directed frob-first path, no make available) gets NO stale-native
guard, while `make check` does -- a real no-Makefile workflow-parity gap,
not just a doc-naming one. Wire the staleness check into frob check's own
run path (or an early guard in its CLI entrypoint) so the two are
equivalent, then make check's recipe can drop the separate python -c
invocation.
