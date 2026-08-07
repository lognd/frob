---
id: T-0175
title: 'agent playbook in-repo: kill per-dispatch retreading'
state: done
kind: docs
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/guides/agent-playbook.md
- docs/index.md
- CLAUDE.md
- Makefile
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
Every worktree agent currently re-learns the same session lessons from scratch, and the coordinator's dispatch prompts have grown into essays carrying them. Move the workflow knowledge into the repo: docs/guides/agent-playbook.md covering -- fresh-worktree setup (git merge main FIRST, make core for natives, use uv run frob never the global binary inside worktrees), scope conventions (tickets.md always in scope), evidence recording (CLI from a natives-built checkout, node-id forms), gate measurement discipline (frob check --delta against the stamped baseline instead of stash-isolation dances -- verify the existing check_delta/stamp_baseline machinery works for this and document the exact commands), Done-report requirements (measured numbers only, honest disclosure of cuts), waive discipline, the deletion-filter land rule, and ledger-conflict splice guidance. Link from CLAUDE.md so agents load it; add a make target or script for the worktree warm-up steps. ALSO: shared natives -- investigate making fresh worktrees inherit prebuilt strata-core/frob_core artifacts (shared cargo target dir via CARGO_TARGET_DIR, or a wheel cache reused by make core) so make core in a worktree is seconds, not minutes; document the mechanism in the playbook.