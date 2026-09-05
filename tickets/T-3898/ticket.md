---
id: T-3898
title: echo the bound acceptance criterion text after --accepts binds it
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
- src/frob/tickets/_evidence.py
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
## Description
Follow-up to T-3837 (frob ticket evidence --accepts N was 0-indexed and
silently accepted a wrong index). T-3837 fixed the base itself (switched
--accepts to 1-based, matching frob ticket show's own [N] display) and
made the out-of-range case a loud typed refusal, both landed on main.

During that work a second agent in the same repo independently measured
--accepts BEFORE T-3837 landed and found it 1-based, while the ticket
body (and this agent's own from-scratch measurement of the pre-fix code)
found it 0-based -- a real disagreement between two careful agents
looking at the same flag. Both were right about different points in
time (pre-fix: 0-based, i < 0 or i >= len; post-fix, now on main:
1-based, i < 1 or i > len) -- but the fact that this took two agents and
a live disagreement to resolve is itself evidence that a caller has no
reliable way to discover the base from the tool alone.

T-3837's fix already covers two of the three asks that came out of that
disagreement:
- --help now states the base explicitly ("1-based ticket.acceptance
  position (T-3837; see `frob ticket show`'s [N] list)") on all three
  --accepts flags (evidence/close/reverify).
- The base now agrees with `frob ticket show`'s own [N] display
  numbering (both 1-based).

The third ask is NOT yet built: an ECHO of what --accepts actually
bound -- print the criterion TEXT the index resolved to (not just the
index number back), so an operator sees the binding at the moment it
happens instead of trusting an index. This converts any future silent
mis-binding (a different index scheme, a fat-fingered number, or a
consumer running a different frob version with different semantics)
into something visibly wrong on the terminal immediately, and makes the
base question moot for whoever is watching the command run.

## Plan
- In `frob.tickets._evidence.add_evidence`/`add_cmd_evidence`
  (`_append_evidence_and_write`'s caller side), after a successful
  accepts-bind, log an INFO line per bound index naming BOTH the 1-based
  position and the criterion's own `text` (e.g. "bound to acceptance [2]:
  <criterion text>"), mirroring `frob ticket show`'s own `_render_acceptance`
  formatting so the two surfaces read identically.
- Add a MUST-FIRE test: binding via --accepts logs the exact criterion
  text, not just the index. MUST-STAY-QUIET: a call with no accepts
  logs nothing extra.