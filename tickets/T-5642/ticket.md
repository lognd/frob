---
id: T-5642
title: 'frob agent precheck: run the recorded pre-land refusal classes inside the
  worktree'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: coord-surface
runs_last: false
milestone: v0.535.0
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
- src/frob/_cli_parsers/_core.py
- src/frob/agent/_precheck.py
- tests/unit/agent/test_precheck.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/agent/_precheck.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/agent/test_precheck.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: sprint
  old_value: null
  new_value: coord-surface
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob agent precheck [<ticket>]: run, inside the worktree, the recorded pre-land refusal classes the dry-run does not measure, each as a named check with a positive control and a must-stay-quiet control: (1) ticket state can transition to done (T-5438); (2) every frob:tests target resolves to a collected node id, so a bare function id of a parametrized test is flagged with the concrete ids (T-draft-4227f6ef); (3) every DOC006-shaped pointer in touched docs resolves on dev, so a path or dotted module pointer to a still-queued sibling is flagged (2026-09-24 refusals on T-5361/T-5362/T-5366); (4) post-squash self-conformance and DOC006 on touched files (T-5403 gap); (5) native extensions fresh vs their source and the interpreter the land will use (T-5518, T-draft-90b33f19); (6) worktree venv has every optional extra (uv sync --all-extras), since a missing extra produced spurious ty refusals on three tickets. Exit non-zero with the list; zero findings prints zero, never skipped.
