---
id: T-2551
title: 'COV007 is mis-scoped for files with no public surface: 78 findings in scripts/
  and .claude/hooks/'
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
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
78 of COV007's 139 live findings sit in files that have no public API
surface at all, so the rule's stated remedy is unachievable there:

  scripts/fleet_status.py                    40
  .claude/hooks/root-write-guard.py          28
  .claude/hooks/root-cleanliness-detector.py  6
  .claude/hooks/_agent_context.py             4

These are standalone executables (a coordinator script, three git/agent
hooks). Their entire callable surface is `main()` plus module-private
helpers and constants by deliberate convention -- several of them
(`scripts/fleet_status.py`) additionally contract to import nothing from
`frob` at all. COV007 tells each one to "move it onto the public caller";
there is no public caller, and moving 40 per-constant anchors onto
`main()` would collapse 40 distinct doc obligations into one and destroy
the per-symbol digest binding that makes AFFECT001/DRIFT001 fire when the
documented thing changes. Following the rule would make the doc graph
strictly worse.

A rule that fires on 100% of the documented symbols in a file class, with
a remedy that class cannot perform, is mis-scoped rather than right-and-
noisy.

OPTIONS (owner decision):
- scope COV007 to library source roots (src/**), the only place a
  "public API surface" exists to move an anchor onto;
- or treat a module with NO public symbols at all as out of scope for
  COV007, which is the same rule stated structurally;
- or leave it and accept 78 boilerplate waivers, which is the outcome
  this repo has already reached ~100 times for the same code (see the
  identical T-1636/T-0871 COV007 waiver texts repeated across
  _land_cmd.py, dup/_core.py, doctor.py, ...).

Filed from T-2370's triage. Does NOT block T-2370's zero half by itself,
but T-2370 cannot reach zero -- and so must not be promoted to ERROR --
until this and T-2549 are decided.
