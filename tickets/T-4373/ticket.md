---
id: T-4373
title: 'COV007: frob:doc on private symbol _resolve_kill_argv (T-4369 introduced)'
state: done
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
- src/frob/tickets/_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: T-4373's fix is a comment-only frob:doc directive removal; BUG002 needs
    an explicit no-behavior-change declaration since there is no runtime defect for
    a test to fail against
  actor: logan
  at: '2026-09-09'
  old_length: 983
  new_length: 1231
evidence:
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
gate:COV COV007 (error-severity) fires on main, failing the ubuntu self-gate step (gh run 34358765772, job 102490073727: frob check . [FAIL] 1 error 5260 warnings). Exact finding text: 'src/frob/tickets/_mutation_evidence.py:296  COV007  COV007: frob:doc on private symbol src/frob/tickets/_mutation_evidence.py::_resolve_kill_argv -- doc anchors normally cover the public API surface; move it onto the public caller, or confirm this private helper genuinely needs its own doc anchor'. Ubuntu was green on the prior push 83a0cecd0; attributed to T-4369 (commit 387caa239), which added the frob:doc docs/modules/tickets-landing.md#mutation-evidence-obligation-test016-t-0755 directive directly on the private _resolve_kill_argv function instead of its public caller. Fix: move the frob:doc anchor onto the public symbol that calls _resolve_kill_argv (per COV007's own remedy text), or add a frob:waive COV007 with a genuine justification if the anchor must stay on the private helper.

frob:no-behavior-change reason="removing a redundant frob:doc directive comment off a private helper is a metadata-only edit -- no runtime code path changes; the bound evidence test is expected to pass identically at both main and the fix commit"