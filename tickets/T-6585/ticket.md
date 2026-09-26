---
id: T-6585
title: 'ticket import-as-done: a sanctioned path to record historical work finished
  before frob existed (explicit flag, recorded reason, no evidence)'
state: queued
kind: feature
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: null
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
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/_cli_parsers/_ticket/
- docs/modules/tickets.md
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
Reported by the project-hullbreach session (2026-09-26): three Sprint-0
Jira items (mockups, a requirements doc, repo setup) were finished before
frob was wired in. `frob ticket close --no-behavior-change` refuses with
MissingEvidence for kind=feature and `--evidence-cmd` is refused for
non-docs/ux kinds (CMD_EVIDENCE_ALLOWED_KINDS), so historical work cannot
be recorded as done; the importer leaves them queued with a label.
Verified on dev b41443f46d: no `--historical`/`--imported` idiom exists
on new or close.

Deliver (tiered safety: a real decision, so an explicit flag):
`frob ticket close <id> --historical --reason TEXT` (or `new --state done
--historical --reason`) that closes without evidence, records the
override in the force-override trail with the reason and the external
reference (e.g. the Jira key), stamps `origin: import` so TICK/COV rules
never expect evidence from it, and excludes it from velocity/points
burndown unless `--count-points`. Refuse when the ticket has a worktree or
lease (it is not historical then). Positive control: a fixture ticket
closes with the flag and the trail carries the reason; the same close
without the flag still refuses with MissingEvidence.
