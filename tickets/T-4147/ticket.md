---
id: T-4147
title: route FLAGCOV001 parser import through the target project's own interpreter
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
T-3887 F-012: FLAGCOV001 imports the target project's own parser (e.g. stpone.flash.cli:build_parser) from frob's own interpreter, so it cannot resolve for any non-frob project (reports UNRESOLVED). frob.process._project_tool (T-3887/T-4125) only covers SUBPROCESS spawns (uv run --project ...); an import is resolved in-process and needs a different mechanism (spawn a resolver subprocess in the project's env and pass the result back, or importlib against the project's own sys.path/venv site-packages). Enumerate every import/exec-in-frobs-interpreter site first (this is likely not the only one), then decide the mechanism. Off-repo fixture required per T-3887's own doctrine: verify against a project whose package is not importable from frob's interpreter.