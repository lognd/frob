---
id: T-2053
title: Cheapen land's post-merge check_gates re-verification spawn (T-0754)
state: done
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_verify.py
- tests/unit/test_ticket_runner_designate_repro.py
- tests/unit/test_ticket_runner_gate_findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_designate_repro.py
  reason: 'T-1344 follow-up: _verify.py''s test coverage lives in these files'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: 'T-1344 follow-up: _verify.py''s test coverage lives in these files'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_check_gates_summary_fn_and_check_gate_findings_fn_share_one_spawn
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Follow-up to T-1344 (investigation, landed a523fa4f5620): land()'s
post-merge re-verification (_check_gates_summary_fn, T-0754) spawns a
fresh, effectively-unscoped `frob check --ticket <id> --json` inside the
land lock on every land -- measured 208.7s live, sitting between the
land-path's own measured median (95.4s) and p75 (322.6s). This is the
single largest directly-measured cost inside a typical land.

Coordinator has asked this be worked in-scope of _verify.py only (owned,
free), without weakening what T-0754 actually verifies (ClaimDivergence
detection between a Done report's captured gate state and the post-merge
tree). See docs/guides/agent-playbook.md section 13 for the full writeup.