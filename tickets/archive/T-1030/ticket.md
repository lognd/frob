---
id: T-1030
title: agent worktree creation cuts from stale base (fa606fe8/b3589c3e) instead of
  main tip -- recurred 3+ times
state: done
kind: bug
origin: agent
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- docs/guides/agent-playbook.md
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/integration/test_interfaces.py
  reason: docs-only ticket has no coverable code symbol; scoping the existing CLI-dispatch
    integration test file itself so its node id can bind evidence coverage per gates.evidence_covers_scope
    route 2 (T-0167 precedent), no new test written since none is warranted
  actor: logan
  at: '2026-07-27'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: GIVEN a fresh dispatch worktree THEN its base contains local main's tip or
    the playbook's warm-up section documents the mandatory fix prominently
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
---
Three separate dispatch batches now had implementer worktrees cut from a stale base (origin tip b3589c3e era, or fa606fe8 -- 20+ files behind main): T-0958-era batch (2 agents), wave-9 gates-tests agent, wave-9 T-1018 agent (pre-filing tip). Playbook workaround (verify merge-base, git merge main) works but every agent pays it. Root-cause where the harness worktree-creation picks its base (likely origin/main or a cached default-branch ref while local main is 240+ commits ahead and never pushed) and document the definitive mitigation in the playbook; if the base choice is outside frob's control, make the playbook warm-up step a hard MUST with the exact two commands.