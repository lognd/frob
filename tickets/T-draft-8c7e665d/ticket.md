---
id: T-draft-8c7e665d
title: 'Claude Code hooks: 10% precision on frob-suggest, double registration doubles
  the attempt counter, blind FROB_SUGGEST_ACK on 97% of uses, no logging'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: story
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: story is a tracking parent; work happens in 4 leaf tickets
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: append
  reason: '2026-09-19: record the cross-story ordering on .claude/hooks/tool-call-telemetry.py
    before either agent starts'
  actor: logan
  at: '2026-09-19'
  old_length: 336
  new_length: 1095
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Audit at scratchpad/HOOK-AUDIT.md. frob-suggest.py precision 10.4%, dual hook registration double-counts attempts per Bash call, FROB_SUGGEST_ACK is a blind blanket bypass used blindly in 97.3% of uses, hook logs nothing. Story tracks 4 leaves: registration/counter fix, rule verdict narrowing, per-rule ack token, and decision logging.

ORDERING NOTE (coordinator via planner, 2026-09-19): this story's leaf T-draft-706ae266 ('frob-suggest: log every block/allow/ignored-ack decision to .frob/telemetry.jsonl') declares scope .claude/hooks/*, which covers .claude/hooks/tool-call-telemetry.py. T-4689 (CLI debloat story T-4687, 'Telemetry records the verb and subverb of every frob invocation') also edits that file and LANDS FIRST. T-4689 makes every frob invocation record verb and subverb (91% of the 34388 telemetry rows carry an empty subcommand today; every kind=tool row is empty because this hook never parses the frob verb out of the Bash command it records). Build the kind=hook rows on top of the fields T-4689 introduces rather than inventing a second row shape for the same stream.