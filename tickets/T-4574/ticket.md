---
id: T-4574
title: WIRE001 cannot resolve cross-file callers through .claude/hooks/ sys.path imports
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3851: .claude/hooks/_shellscan.py::strip_and_blank_prefixed_segments is called by .claude/hooks/frob-suggest.py::_handle_bash (from _shellscan import strip_and_blank_prefixed_segments as _strip_and_blank, after sys.path.insert(0, str(Path(__file__).resolve().parent))) in the SAME diff, yet WIRE001 reports it as having 'no caller outside its own tests'. Pre-existing cross-file symbols in _shellscan.py (POS, strip_quoted) are never checked by WIRE001 because they are not NEW in any diff, so this blind spot has never been exercised before. Root cause suspected: WIRE001's call-graph resolver does not trace calls through .claude/hooks/**'s dynamic sys.path.insert + bare-module-name import pattern. Waived on T-3851 with a note; this ticket tracks fixing or explicitly documenting the resolver gap.