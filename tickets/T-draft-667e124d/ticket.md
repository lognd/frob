---
id: T-draft-667e124d
title: New advisory Severity tier that never fails a gate (LAUNCH family)
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5140
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_models.py
- frob.toml
- docs/modules/gates.md
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
OWNER DIRECTIVE: LAUNCH gets a NEW `advisory` Severity tier, not a never-fail flag bolted onto `warn`. Locate the existing Severity enum (grep frob.gates for `class Severity` -- likely src/frob/gates/_models.py or frob/findings) and add ADVISORY as a real member; the finding-rendering path (`frob check` output, `--report` surfaces) must render advisory findings distinctly from warn (never counted toward a non-zero exit, never gate-blocking, still visible). [gates.severity] parsing must accept the string 'advisory' as a valid per-rule override value. T-5145-6 (LAUNCH checklist) blocks on this leaf. Doc: docs/modules/gates.md's severity-tier explanation.