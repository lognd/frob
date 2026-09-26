---
id: T-6572
title: land --dry-run still skips the scoped ruff check the real land runs, so a dry
  run stays green on a new E501 in a touched file (T-5161 follow-up)
state: queued
kind: bug
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
- src/frob/app/ticket_runner/_land_cmd.py
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
Reported by the crunk session (2026-09-26) on frob 0.531.1.dev338, which
already carries T-5161 (dry-run runs the unscoped pre-land sweep): `frob
ticket land --dry-run` for crunk T-0169 reported "DRY RUN clean,
merged=True" and the real land then refused on a NEW ruff E501 in a
touched file. The scoped ruff pass the real land runs on touched files is
not part of the dry run (T-4179 keeps only the format would-rewrite
probe), so the dry run is a false green for lint.

Deliver: --dry-run runs the same scoped ruff check (read-only, same rule
selection and same touched-file set) and reports its findings alongside
the T-5161 sweep preview; the DRY RUN summary names each pre-land probe
it ran so a "clean" is auditable. Positive control: a fixture worktree
with one over-long line in a touched file; the dry run reports E501 and
the real land refuses on the same finding.
