---
id: T-2909
title: 'Agent cold-start: split agent-playbook.md into a hot-path checklist plus an
  appendix'
state: in-progress
kind: docs
origin: human
created: '2026-08-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/agent-playbook.md
- docs/guides/agent-playbook-appendix.md
- docs/audits/test005-zero-classification-t1418.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/guides/agent-playbook.md
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/guides/agent-playbook-appendix.md
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/audits/test005-zero-classification-t1418.md
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/tickets/_worktree_sweep.py
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: add
  glob: .claude/hooks/sync-claude-config.py
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: add
  glob: .claude/refs/frob.md
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/guides/agent-playbook-appendix.md
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/audits/test005-zero-classification-t1418.md
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/tickets/_worktree_sweep.py
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: add
  glob: .claude/hooks/sync-claude-config.py
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: add
  glob: .claude/refs/frob.md
  reason: split playbook into hot-path checklist + appendix, update all references
  actor: logan
  at: '2026-08-25'
- op: remove
  glob: src/frob/tickets/_worktree_sweep.py
  reason: not touched; narrowing to actually-modified files
  actor: logan
  at: '2026-08-25'
- op: remove
  glob: .claude/hooks/sync-claude-config.py
  reason: not touched; narrowing to actually-modified files
  actor: logan
  at: '2026-08-25'
- op: remove
  glob: .claude/refs/frob.md
  reason: not touched; narrowing to actually-modified files
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
