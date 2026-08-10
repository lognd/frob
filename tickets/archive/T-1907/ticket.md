---
id: T-1907
title: Rapid-profile land does not gate on the type family, so type errors land and
  the post-land sweep files them after publication
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_work_and_land_finish.py
- src/frob/tickets/_land_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'T-1907''s fix: unconditional touched-file ty guard in _land_cmd.py, its
    regression tests, and the loud UNKNOWN-not-clean disclosure in _land_verify.py''s
    claims early-out'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: 'T-1907''s fix: unconditional touched-file ty guard in _land_cmd.py, its
    regression tests, and the loud UNKNOWN-not-clean disclosure in _land_verify.py''s
    claims early-out'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/tickets/_land_verify.py
  reason: 'T-1907''s fix: unconditional touched-file ty guard in _land_cmd.py, its
    regression tests, and the loud UNKNOWN-not-clean disclosure in _land_verify.py''s
    claims early-out'
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_a_type_error_in_a_touched_file_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestReverifyDoneReportClaimsDisclosesUnknownGateState::test_no_captured_claims_section_logs_unknown_not_clean
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error
designated_repro_test: tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09, coordinator, across one dispatch wave on main. Every one of these was filed by the DEFERRED post-land sweep against an ALREADY-PUBLISHED commit:

  T-1894  invalid-argument-type x3  <- T-1880's land (c9fa9f2c6206)
  T-1896  invalid-argument-type x3  <- T-1872's land (d241bcd7201c)

Both were real static errors (dict vs Mapping invariance on scope_lease_conflict; None passed to a non-Optional GraphSnapshot parameter). Neither was a runtime bug, and neither was caught before publication.

ROOT CAUSE. Under the rapid profile the pre-land verification is relaxed (T-1575/T-1681) and the type family is not among what remains. Agents verify with scoped 'frob check --ticket <id> --only ...' selections that omit the type gate, land green, and the detached sweep discovers the error afterwards. The check exists and runs -- one commit too late.

INDEPENDENT CORROBORATION. The implementer that fixed T-1894/T-1896 reached the same conclusion unprompted and recommended: run the type gate scoped to touched files as a standard step before 'ticket close', not just before land.

WHY IT MATTERS. It is a per-land tax: each occurrence costs a full extra dispatch cycle (file ticket, brief agent, worktree, fix, land, sweep again). It also erodes the meaning of 'landed green'. And the sweep's own filing text invites dismissing a real error -- it offers 'pre-existing residue the rolling baseline had not recorded yet' as an explanation, which a hurried reader will take.

THE DEEPER ISSUE -- 'UNKNOWN' IS BEING READ AS 'CLEAN'. frob already tells the truth about this in the gate:scope-note warning: '--only ran 2/43 gate famil(ies); NOT run this invocation (status unknown, not clean)'. Nothing downstream acts on that distinction. A ticket whose recorded evidence never ran a gate family should not be landable as though that family passed.

PROPOSED FIX (decide on merit):
1. Add the type check to the MINIMUM pre-land gate the rapid profile may NOT relax, restricted to the ticket's touched files so it stays cheap.
2. Make 'frob ticket land' refuse -- or at minimum loudly disclose -- when the ticket's recorded gate evidence never ran a family at all. Treat unknown as unknown.
3. Regression test: a worktree whose diff introduces a type error must be REFUSED at land under the rapid profile, not landed-then-swept.

Related: T-1894, T-1896, T-1902/T-1905 (the same land-green-then-break-main shape via a contract tightening), T-1903 (a guard sequenced before the mutation it verifies), and the T-1681 re-verification debt.