---
id: T-3473
title: may-raise resolver cannot track regex-group digit-safety through a None-checked
  match object
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_mayraise.py
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
follow-up split off T-2568 (isdigit-guard discharge). scripts/_require_python.py::_required_version and scripts/wait_for_land_slot.py::probe_lands_in_flight both guard int(match.group(N)) with 'if match is None: return' where match comes from a module-level compiled regex whose group N pattern is provably \\d+-only -- genuinely safe, but requires tracking a module-level re.compile() constant's pattern text through a local match-object binding to its .group() call, real local flow (T-2568's option 2), not a text-adjacency guard match. EXHAUST002 findings: scripts/_require_python.py:31, scripts/wait_for_land_slot.py:151.