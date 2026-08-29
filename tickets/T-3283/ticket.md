---
id: T-3283
title: '6 of T-3041''s 13 live-repo self-conformance tests fail again: genuine post-close
  drift, not a stale claim'
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_frob_self_model.py
- tests/unit/strata/test_selfconform.py
- tests/unit/strata/test_conform_eval_needle.py
- tests/test_docptr_gate.py
- tests/test_registry_exhaustiveness.py
- docs/design/registry/check-coverage.yaml
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
- src/frob/gates/_empty_diff_close.py
- tickets/T-3262/ticket.md
- tickets/T-3287/ticket.md
- tickets/T-3324/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: T-3283's fix for the SYS gate/selfconform failures lives in design/frob.strata
    (7 undeclared SYS100 capability grants from ~9 unrelated post-T-3041 lands) plus
    its ratchet lock, and TICK014's missing frob:enforces directive in empty_diff_close.py
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: T-3283's fix for the SYS gate/selfconform failures lives in design/frob.strata
    (7 undeclared SYS100 capability grants from ~9 unrelated post-T-3041 lands) plus
    its ratchet lock, and TICK014's missing frob:enforces directive in empty_diff_close.py
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_empty_diff_close.py
  reason: T-3283's fix for the SYS gate/selfconform failures lives in design/frob.strata
    (7 undeclared SYS100 capability grants from ~9 unrelated post-T-3041 lands) plus
    its ratchet lock, and TICK014's missing frob:enforces directive in empty_diff_close.py
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-3262/ticket.md
  reason: T-3283's DOC006 fix corrected/waived the two false-positive doc pointers
    found in these tickets' own bodies (T-3262's mis-typed scaffold invocation, T-3287's
    ephemeral worktree-path illustrations) -- the two responsible tickets for the
    DOC006 half of the drift
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-3287/ticket.md
  reason: T-3283's DOC006 fix corrected/waived the two false-positive doc pointers
    found in these tickets' own bodies (T-3262's mis-typed scaffold invocation, T-3287's
    ephemeral worktree-path illustrations) -- the two responsible tickets for the
    DOC006 half of the drift
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-3324/ticket.md
  reason: T-3324 was filed from within this worktree as T-3283's own explicit ask
    (record the structural landing-time-enforcement finding as a follow-up ticket)
  actor: logan
  at: '2026-08-28'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
- tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
- tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3041's Done report claimed 13 live-repo self-conformance tests were all
either fixed (5 by T-3029, 4 more by T-3041 itself: test_effects.py +
3 export_golden goldens) or filed as separate tickets (T-3223 DOC006,
T-3224 REG005/REG008, T-3225 WAIVE006), and stated the 5 fixed-by-T-3029
claim was "confirmed by re-running them fresh on main post-T-3029".

Baseline measurement on today's main shows 6 of T-3041's exact 13 node
ids failing again:

  tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
      -- 41 SYS violations, ran to completion in 358.89s under --timeout=0
         (NOT a timeout)
  tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean@selfconform-full-repo-scan
  tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant@selfconform-full-repo-scan
  tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
  tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo (DOC006: 50 findings)
  tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml (REG008: 9 findings)

DETERMINATION (this ticket's own job): GENUINE REGRESSION, not a stale
claim. Verified directly rather than guessed, per land-history bisection:

1. test_sys_gate_zero_violations and test_conform_eval_needle: checked
   out T-3041's own land commit (034f4fbae), built natives fresh
   (`uv run frob natives build` -- the checkout had none, T-2409-class
   worktree-natives gap, distinct from the actual defect), and ran both
   directly (bypassing pytest-timeout's addopts-baked 120s/xdist, which
   otherwise crashes the worker on these known-slow whole-repo scans:
   `-o addopts="" -p no:xdist`). Both PASSED at 034f4fbae (81s and
   57.79s respectively) -- T-3041's "confirmed fresh on main" claim was
   TRUE when made.

2. test_docptr_gate.py and the REG008 case: at T-3041's own land commit
   (034f4fbae) both FAILED, as expected -- T-3041 explicitly deferred
   these to the separately-filed T-3223/T-3224, not fixed by T-3041
   itself. Checked out T-3224's land commit (0b723f1fe, which is after
   T-3223's 733b01eae) and re-ran both: ALL 67 collected tests in those
   two files PASSED cleanly (109.60s) -- T-3223/T-3224's fixes were
   real and complete at the time they landed.

3. So every one of the 6 now-failing tests was genuinely green
   immediately after its respective fixing ticket landed. Between then
   and today's main, unrelated ticket lands accumulated new drift onto
   the same shared self-conformance surface -- e.g. 3 separate
   subsequent commits (T-3092, T-2988, T-3228) each appended new entries
   to docs/design/registry/check-coverage.yaml (the exact file T-3224
   fixed) without re-establishing REG008 exhaustiveness, and ~30
   intervening ticket lands between T-3041's close and T-3224's close
   touched shared design/doc/registry surface between the two
   test_conform_eval_needle measurements above.

This matches an existing, already-recognized pattern in this repo:
4 "post-land sweep regression" tickets (T-3227, T-3236, T-3237, T-3238)
already track the same class of drift -- individually-reasonable ticket
lands cumulatively pushing this self-referential repo's own
self-conformance gates back to non-zero. These 6 test failures are that
same mechanism observed through the direct pytest lens instead of the
sweep's lens.

FINDING ABOUT CLOSURE VERIFICATION (asked for explicitly): T-3041's
"confirmed by re-running fresh on main" claim was procedurally sound --
it measured what it said it measured, at the time it said it did. The
failure mode here is NOT a bad closure verification; it is that
"clean against a live, actively-changing repo" is not a fact that stays
true -- these 6 tests assert a live-repo invariant that any of ~40
unrelated, individually-correct ticket lands can silently violate, and
none of those lands' own gates catch cross-ticket self-conformance drift
(each land's `frob check` scopes to its own diff). Worth naming plainly:
closure claims of the form "verified clean against the live repo" need
either (a) re-verification close to consumption, not trusted indefinitely,
or (b) the underlying invariant enforced as a landing-time gate so no
individual land can silently break it, not just measured after the fact
by a slow full-repo test. T-3247 (landed after T-3041) already had to
raise these same tests' timeouts specifically because whole-repo scans
are expensive -- that cost is likely why this class of drift is caught
late (a slow full test) rather than early (a fast per-land gate).

Do NOT reopen T-3041 -- its own claim was accurate when made and its own
scope (5+4 tests, fixed in-ticket) was fully discharged; it is not the
right owner of new drift accumulated by ~40 later, unrelated tickets.

ACCEPTANCE
- Each of the 6 re-failing node ids is either fixed or has its exact
  current finding set (SYS/DOC006/REG008 violations, with concrete
  file:line content, not just a count) attributed to a specific
  responsible ticket/change.
- docs/design/registry/check-coverage.yaml's REG008 exhaustiveness is
  restored (or a `frob:waive REG008 follow_up="T-####"` recorded per
  entry, per the established idiom -- never a bare waiver).
- Whoever picks this up should decide whether one of (a)/(b) above is
  worth doing as follow-on scope, not silently declined.