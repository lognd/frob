---
id: T-2393
title: BUG002 has no front door for tickets with no behavioral delta
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/config.py
- tests/test_bug002_no_behavior_change.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: 'T-2393: surface frob:no-behavior-change as a first-class frob ticket close
    flag, replacing the hand-edit-only remedy'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: 'T-2393: surface frob:no-behavior-change as a first-class frob ticket close
    flag, replacing the hand-edit-only remedy'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-2393: surface frob:no-behavior-change as a first-class frob ticket close
    flag, replacing the hand-edit-only remedy'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_bug002_no_behavior_change.py
  reason: 'T-2393: surface frob:no-behavior-change as a first-class frob ticket close
    flag, replacing the hand-edit-only remedy'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/_config_external.py
  reason: T-2387 landed and released its lease; wire the T-2392/T-2393 AppConfig fields
    into the argparse Namespace copy (the follow-up recorded as T-2402)
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_bug002_no_behavior_change.py::TestNoBehaviorChangeCli::test_flag_writes_directive_before_close
- tests/test_bug002_no_behavior_change.py::TestNoBehaviorChangeCli::test_reason_missing_exits_nonzero
- tests/test_bug002_no_behavior_change.py::TestNoBehaviorChangeCli::test_flag_absent_is_a_no_op
- tests/test_bug002_no_behavior_change.py::TestGateNotWeakened::test_confirmatory_only_without_directive_still_refused
- tests/test_bug002_no_behavior_change.py::TestGateNotWeakened::test_directive_present_inverts_to_must_still_pass
- tests/test_bug002_no_behavior_change.py::TestRealArgvParsing::test_close_no_behavior_change_flags_survive_real_argv_parsing
- tests/test_bug002_no_behavior_change.py::TestRealArgvParsing::test_body_append_flags_survive_real_argv_parsing
designated_repro_test: tests/test_bug002_no_behavior_change.py::TestNoBehaviorChangeCli::test_flag_writes_directive_before_close
acceptance:
- text: Given a doc-only, epic-rollup, or purely structural ticket, when it is closed
    with an explicit mandatory reason, then BUG002 accepts it via a first-class CLI
    flag without any ledger hand-edit, and the reason is recorded.
  evidence:
  - tests/test_bug002_no_behavior_change.py::TestNoBehaviorChangeCli::test_flag_writes_directive_before_close
- text: Given a ticket with genuinely confirmatory-only evidence and no such flag,
    when it is closed, then BUG002 still refuses, proving the gate was not weakened.
  evidence:
  - tests/test_bug002_no_behavior_change.py::TestGateNotWeakened::test_confirmatory_only_without_directive_still_refused
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: 74904cd65d663658b50a6566f3f1298b52f1ba5f
---
MEASURED TODAY: three separate tickets were blocked at close/land time
by BUG002 (`EvidenceConfirmatoryOnly`) despite having no runtime defect
to reproduce -- T-1662 (epic closure, kind=security), T-2341 (kind=bug
but every change structural/doc), and T-2346 (needed
`--designate-repro-force` for a related reason).

The gate is CORRECT in general: evidence must fail at the parent commit,
not merely confirm current behaviour. But a ticket whose deliverable is
documentation, an epic rollup, or a pure structural refactor has no
behavioural delta to demonstrate, and the gate has no way to know that.

A remedy already exists -- `frob:no-behavior-change reason="..."` in the
ticket body -- but it is reachable ONLY by hand-editing the ledger
(see T-2392), so the safe path and the available path diverge.

FIX: surface the existing remedy as a first-class flag, e.g.
`frob ticket close --no-behavior-change --reason TEXT`, writing the same
directive through the validated mutation path. Keep the reason
MANDATORY -- this must stay prove-or-justify, not an escape hatch. Do
NOT weaken BUG002 itself; the gate has caught real confirmatory-only
evidence and `--check-repro` runs in ~1.5s. The defect is the missing
front door, not the lock.