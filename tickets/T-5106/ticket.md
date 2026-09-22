---
id: T-5106
title: 'frob ticket land --queue: the coordinator needed five scratchpad shell scripts
  (queue-runner, land-one, chain, dispose-noise, push-if-idle) to serialize lands,
  merge dev with dev winning on land-owned files, retry a lost CAS, follow a draft
  promoted on dev, wait for a clean root, kill a lock-holding sweep, and gate pushes
  on CI idle; all of that is one verb frob must own'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-4654
tier: story
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
- field: tier
  old_value: ticket
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
- field: parent
  old_value: null
  new_value: T-4654
  reason: land-queue-as-default is the LAND concern's throughput story
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: land-queue-as-default is a story of the land
    kernel (T-4654)'
  actor: logan
  at: '2026-09-21'
- field: tier
  old_value: story
  new_value: story
  reason: 'owner decision 2026-09-21: the land queue as default path is a story of
    the land kernel (T-4654), not one ticket'
  actor: logan
  at: '2026-09-21'
body_changes:
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 0
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
- mode: set
  reason: design after mapping the existing queue machinery (T-1345/T-3613) and the
    v0.535.0 land-kernel plan
  actor: logan
  at: '2026-09-21'
  old_length: 2259
  new_length: 2259
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
STORY (owner decision 2026-09-21): the land queue is the default land path and needs no wrapper.

WHY. frob already ships the queue (T-1345 enqueue/drain_next/QueueEntry, T-3613 default-to-queue under FROB_AGENT or `ticket_land_default = "queue"`, `--status` intent records, T-3614 --wait). Three coordinator sessions still rebuilt a shell runner around it (queue-runner, land-one, hygiene, adopt-drafts, dispose-noise), because the drain does not do what every land needed: drafts filed inside worktrees break sibling finalize (T-5166), promoted-draft dirs survive the merge (T-4571), land-owned files conflict on every dev merge (T-5162), post-land sweep residue raises the quarantine and forces every following land synchronous (T-4611/T-4603), a refused land leaves state=done and staged land-owned files in the worktree, the drain is FIFO with no blocked_by order, and nothing owns the drainer's lifecycle or exposes it to agents. The trigger for needing a queue is concurrency (more than one live lease), not repo size.

SHAPE. Each leaf hooks an existing seam: `_apply_land_default_queue`/`_dispatch_land_mode` (mode ladder), `QueueEntry`/`drain_next` (selection), T-4738's prepare phase (hygiene lives in prepare, never in the detached post-land sweep per T-4414), `_land_finalize` unwind (clean refusal), `frob serve` `_daemon.py` poll set (drainer lifecycle, no third daemon), `serve/_tools.py` `Result[dict, ServeError]` tools (MCP). Config stays flat under `[tool.frob]` per convention. The land's CLI surface and refusal vocabulary do not change (T-4654 frozen contract).

DONE MEANS. An agent under FROB_AGENT runs a bare `frob ticket land <id> --worktree P`, it returns in seconds, the daemon lands it in dependency order without a coordinator script, a planted refusal leaves the worktree clean and the intent record names the refusal, `frob status` shows the queue and a stuck land, and the MCP tools report the same. Positive control: an e2e that enqueues three tickets out of blocked_by order plus one planted refusal.

Repo set to `ticket_land_default = "queue"` on 2026-09-21 (commit 69b4468f5d). NOTE: the documented key `land_default` is not read; the loader merges by AppConfig field name (leaf A fixes the docs and adds the opt-out).
