---
id: T-3748
title: 'reuse: run the suite once with --cov in the Test step and stamp coverage from
  that, instead of a second full-suite run'
state: queued
kind: feature
origin: human
created: '2026-09-03'
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
- src/frob/app/coverage_runner.py
- src/frob/app/_config_external.py
- .github/workflows/ci.yml
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/**
  reason: add frob coverage --fail-on-degraded so the ubuntu Test step runs the suite
    once with coverage as the pass/fail gate; wire it in ci.yml and drop the duplicate
    coverage-suite run
  actor: logan
  at: '2026-09-03'
- op: add
  glob: src/frob/app/coverage_runner.py
  reason: add frob coverage --fail-on-degraded so the ubuntu Test step runs the suite
    once with coverage as the pass/fail gate; wire it in ci.yml and drop the duplicate
    coverage-suite run
  actor: logan
  at: '2026-09-03'
- op: add
  glob: src/frob/app/_config_external.py
  reason: add frob coverage --fail-on-degraded so the ubuntu Test step runs the suite
    once with coverage as the pass/fail gate; wire it in ci.yml and drop the duplicate
    coverage-suite run
  actor: logan
  at: '2026-09-03'
- op: add
  glob: .github/workflows/ci.yml
  reason: add frob coverage --fail-on-degraded so the ubuntu Test step runs the suite
    once with coverage as the pass/fail gate; wire it in ci.yml and drop the duplicate
    coverage-suite run
  actor: logan
  at: '2026-09-03'
- op: add
  glob: tests/**
  reason: add frob coverage --fail-on-degraded so the ubuntu Test step runs the suite
    once with coverage as the pass/fail gate; wire it in ci.yml and drop the duplicate
    coverage-suite run
  actor: logan
  at: '2026-09-03'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
