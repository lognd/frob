---
id: T-5304
title: New advisory Severity tier that never fails a gate (LAUNCH family)
state: in-progress
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5140
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_models.py
- frob.toml
- docs/modules/gates.md
- src/frob/gates/_waive.py
- src/frob/check/_python.py
- src/frob/gates/_gates_schema.py
- src/frob/findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: advisory Severity tier touches severity-override parsing, exit-code/summary
    rendering, and schema validation, not just the enum definition
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/check/_python.py
  reason: advisory Severity tier touches severity-override parsing, exit-code/summary
    rendering, and schema validation, not just the enum definition
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_gates_schema.py
  reason: advisory Severity tier touches severity-override parsing, exit-code/summary
    rendering, and schema validation, not just the enum definition
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/findings.py
  reason: Severity enum's real definition lives in frob.findings; _models.py only
    re-exports it
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5304
branch: t-5304
---
OWNER DIRECTIVE: LAUNCH gets a NEW `advisory` Severity tier, not a never-fail flag bolted onto `warn`. Locate the existing Severity enum (grep frob.gates for `class Severity` -- likely src/frob/gates/_models.py or frob/findings) and add ADVISORY as a real member; the finding-rendering path (`frob check` output, `--report` surfaces) must render advisory findings distinctly from warn (never counted toward a non-zero exit, never gate-blocking, still visible). [gates.severity] parsing must accept the string 'advisory' as a valid per-rule override value. T-5145-6 (LAUNCH checklist) blocks on this leaf. Doc: docs/modules/gates.md's severity-tier explanation.