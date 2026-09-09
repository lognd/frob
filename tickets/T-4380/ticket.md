---
id: T-4380
title: two files landed unformatted by T-4088 and T-4365 lands
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/perf/_rules.py
- tests/system/test_cli_doctor.py
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
uv run frob format in a fresh worktree off main rewrites two files that
should already be canonical after their own lands:

  src/frob/perf/_rules.py           -- left unformatted by the T-4088 land
  tests/system/test_cli_doctor.py   -- left unformatted by the T-4365 land

frob check already reports this as a WARN-level ruff-format finding
repo-wide (measured while landing T-4374/T-4378 in the prior series:
"[ruff-format] Would reformat: src/frob/perf/_rules.py needs formatting").
The root commit guard refuses a direct coordinator edit outside a ticket,
so this needs its own ticket.

Plan: start this ticket in a worktree, run `uv run frob format`, confirm
`uv run frob check --ticket <id>` reports no FMT/ruff-format finding on
either file, bind evidence with the no-behavior-change declaration (pure
formatting, same shape T-4373 used), land, verify on main.

Also investigate and record in the Done report WHY each land's own
Tier-A format step did not catch this -- if it was skipped (e.g. profile
override, a scope mismatch between the land's Tier-A pass and these
files, or a race), name the mechanism; file a SEPARATE follow-up ticket
for the mechanism itself rather than fixing it as part of this ticket
(this ticket's scope is only the two named files).

Verify: uv run frob check --ticket <id> reports no ruff-format finding
on src/frob/perf/_rules.py or tests/system/test_cli_doctor.py.