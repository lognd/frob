---
id: T-draft-bf260aec
title: 'frob doctor: report lint-tool version lag against latest PyPI/npm/crates release'
state: queued
kind: feature
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/doctor.py
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
T-5138 acceptance [5] (given ruff two minor versions behind PyPI, frob doctor reports the lag) is out of T-5138's declared scope (src/frob/vet/*.py, frob.toml, docs/modules/vet.md, src/frob/strata/_cve_fingerprint.py -- doctor.py is not in it). DESIGN item 7 from T-5138: frob doctor reports installed ruff/ty/mypy/eslint/clippy versions against the latest PyPI/npm/crates release, cached 24h, warns past a configurable lag.