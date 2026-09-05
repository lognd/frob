---
id: T-3911
title: remove frob fmt deprecated alias at sunset (T-3906 follow-up)
state: queued
kind: ux
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/fmt_runner.py
- src/frob/_cli_parsers/_misc.py
- src/frob/app/config.py
- src/frob/app/app.py
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
T-3906 consolidated frob fmt into frob format --directives and kept frob fmt as a frob:deprecated alias, sunset=2026-12-01. When that sunset passes, remove the fmt subcommand registration, fmt_runner.py, and the fmt_* AppConfig fields; keep frob format --directives as the only surface.