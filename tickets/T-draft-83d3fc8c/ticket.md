---
id: T-draft-83d3fc8c
title: 'land prepare: re-sync the worktree venv (uv sync) after the dev merge whenever
  pyproject.toml or uv.lock changed, so evidence collection does not fail on a missing
  dependency'
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
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_lifecycle.py
- docs/modules/tickets-landing.md
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
Reported by the crunk session (2026-09-26): a merge brought in a
dev-dependency added by another ticket (jsonschema); `frob ticket land`
then collected tests with the worktree's EXISTING .venv, which was never
re-synced, so `pytest --collect-only` exited 2 and every evidence id "no
longer resolves". Three tickets hit it; the manual fix was installing the
dependency into each worktree venv. Verified on dev e98e686cbc: `ticket
work` has a venv-sync half (T-3320, _lifecycle.py) but land's prepare
step (merge dev, natives rebuild, ledger align) has no sync; the
coordinator's own hygiene script had to add "deps changed -> uv sync"
keyed on the pyproject.toml/uv.lock tree hash for the same reason.

Deliver (automatic tier, guaranteed safe): after the prepare merge, when
pyproject.toml or uv.lock differs from the pre-merge tip, run the same
`uv sync` step `ticket work` uses inside the worktree (frozen to the
merged uv.lock), log one line naming the changed file, and only then
collect evidence; a sync failure is a refusal naming the command, not a
silent "no longer resolves". Positive control: a fixture where dev adds
a dependency used by the ticket's evidence test; land collects it after
the sync, and without the sync the collection fails.
