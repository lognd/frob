---
id: T-draft-695e4323
title: 'frob check --ticket: refuse a second concurrent full check for the same worktree
  (per-worktree lock), --allow-concurrent to override, so stacked agent checks cannot
  starve the shared host'
state: queued
kind: feature
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/app/check_runner.py
- src/frob/process/
- src/frob/_cli_parsers/_check.py
- docs/modules/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-26'
  old_length: 1530
  new_length: 1530
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured twice on 2026-09-26 (14:00 and 23:05 local): implementer agents
in crunk worktrees stacked two to four concurrent `frob check --ticket`
processes per worktree (17 frob check processes host-wide, load average
46-79), and frob's single-threaded land drain produced no output for
four hours until the load fell. Briefing agents to run one check at a
time worked only until the next dispatch; the crunk coordinator asked
for a frob-side guard.

Owner directive (systematize friction: a repeated friction becomes a
refusal with one override flag; tiered safety: guaranteed-safe runs
automatically). Deliver: (1) `frob check --ticket <id>` (and any full,
unscoped `frob check`) takes a per-worktree lock under .frob/ keyed by
the resolved root; a second invocation while the first is alive refuses
within one second naming the holder pid, its start time and its argv,
exit code distinct from a gate failure; a dead holder's lock is
reclaimed automatically (pid liveness, same probe TICK015 uses); (2)
`--allow-concurrent` overrides for a genuinely intended parallel run and
is recorded in the run log; scoped `--files`/`--only lint` runs are not
locked; (3) `frob coord status` (T-5784) lists live full checks per
worktree so a coordinator sees stacking at a glance; (4) docs/modules/
check.md documents the lock and the override tier. Positive control: a
test that holds the lock with a fake live pid and asserts the second run
refuses naming that pid, and that a stale lock from a dead pid is
reclaimed and the run proceeds.
