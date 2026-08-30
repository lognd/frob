---
id: T-3419
title: 'post-land sweep did not file a real SELFAUDIT001 regression it should have
  caught: findings anchored off-file may be invisible to its identity model'
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_land_finish_idempotent.py
- tests/test_ticket_work_and_land_finish.py
- docs/modules/tickets-verify-sweep.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: identity extraction (_error_finding_identity/_collect_error_findings) that
    collapses SELFAUDIT001/off-file-anchored findings lives in _verify.py, not _rapid_sweep.py;
    sweep consumes the already-collapsed tuple unchanged
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: identity extraction (_error_finding_identity/_collect_error_findings) that
    collapses SELFAUDIT001/off-file-anchored findings lives in _verify.py, not _rapid_sweep.py;
    sweep consumes the already-collapsed tuple unchanged
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_land_finish_idempotent.py
  reason: identity extraction (_error_finding_identity/_collect_error_findings) that
    collapses SELFAUDIT001/off-file-anchored findings lives in _verify.py, not _rapid_sweep.py;
    sweep consumes the already-collapsed tuple unchanged
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: identity extraction (_error_finding_identity/_collect_error_findings) that
    collapses SELFAUDIT001/off-file-anchored findings lives in _verify.py, not _rapid_sweep.py;
    sweep consumes the already-collapsed tuple unchanged
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'scope-closure: _rapid_sweep.py symbols already in scope doc-edge into this
    file'
  actor: logan
  at: '2026-08-30'
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestErrorFindingIdentityOffFileAnchors::test_must_fire_new_selfaudit001_finding_not_deduped_against_unrelated_one
- tests/unit/test_ticket_runner_gate_findings.py::TestErrorFindingIdentityOffFileAnchors::test_must_stay_quiet_no_message_path_falls_back_to_shared_anchor
- tests/unit/test_ticket_runner_gate_findings.py::TestErrorFindingIdentityOffFileAnchors::test_ordinary_per_file_finding_is_unaffected
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_blank_identity_diagnostic_is_dropped_not_added
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_drop_is_logged_naming_the_emitting_tool
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_a_diagnostic_with_only_file_set_is_kept
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_ty_and_gate_error_both_appear_in_parsed_set
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The post-land sweep's attribution engine did not report a real SELFAUDIT001
finding that a land introduced, while correctly reporting SYS003, TEST001 and
WIRE002 findings from the SAME land. The sweep is the mechanism this repo
relies on to catch what a land breaks, so a rule family it cannot see is a hole
in the safety net rather than a reporting nicety.

MEASURED 2026-08-29, across two independent observers.

T-3350's land introduced a cluster of findings by creating src/frob/nodeid.py
without adding it to the design model. The post-land sweep filed T-3413 listing
9 (rule, file) identities / 10 findings. Series EY, working T-3413, reported:

    "My own SELFAUDIT001/SYS102 finding was NOT in T-3413's filed list at all
     -- real (reproduced directly against sys_gate), fixed here too, but the
     post-land sweep's identity model apparently doesn't track SELFAUDIT001 the
     same way it tracks SYS003/TEST001/WIRE001-family rules."

The coordinator's own independent full-tree run (`frob check --no-cache`, idle
box, no REPLAY) confirms SELFAUDIT001/SYS102 was live on main at that time:

    SELFAUDIT001: self-audit family SYS102 node=src/frob/nodeid.py:
    src/frob/nodeid.py has no node's code= glob binding it

So: same land, same root cause, four rule families affected, and exactly one of
them missing from the sweep's filing. This was caught only because an agent
measured the family directly instead of trusting the filed list.

WHY IT MATTERS MORE THAN ONE MISSED LINE. The whole argument for the post-land
sweep is that deferred verification is safe BECAUSE the sweep files what the
land's own gates did not block. If the sweep's identity model silently omits a
rule family, then for that family deferred landing has no backstop at all, and
the omission is invisible: a short filed list looks exactly like a clean land.
That is the dominant defect shape in this repo -- a zero that means "not
measured" wearing the costume of "measured clean".

WHAT TO FIND OUT, in this order. Do not skip to a fix.
  1. Is SELFAUDIT001 absent from the sweep's rule set entirely, or present but
     unable to form a stable (rule, file) identity? SELFAUDIT001 findings are
     reported against `design:1` rather than against the offending source file
     (see the message above -- the finding NAMES src/frob/nodeid.py in its text
     but is ANCHORED at design:1). An identity model keyed on (rule, file)
     would collapse every SELFAUDIT001 in the repo to a single identity and
     could plausibly dedupe a new one against a pre-existing one. Test that
     hypothesis specifically; it also predicts the same bug for any other rule
     that reports against a synthetic anchor rather than a real path.
  2. Enumerate EVERY rule family whose findings anchor somewhere other than the
     offending file, and check each against the sweep's identity model. If the
     hypothesis in (1) holds, SELFAUDIT001 is one instance of a class, and
     fixing only SELFAUDIT001 leaves the rest.
  3. Only then decide the fix.

DO NOT fix this by adding SELFAUDIT001 to a list. If the cause is the identity
model's assumption that a finding's anchor is its subject, a per-rule patch
leaves the same hole for the next rule that violates that assumption.

MUST-FIRE FIXTURE:   a land that newly introduces a SELFAUDIT001 finding is
                     reported by the sweep, and is not deduped against an
                     unrelated pre-existing SELFAUDIT001.
MUST-STAY-QUIET:     a land that introduces no new findings still files nothing.

ACCEPTANCE
- Question (1) answered with file:line, not inferred.
- The full enumeration from (2) reported, even if the answer is "SELFAUDIT001
  is the only one".
- Both fixtures committed.
