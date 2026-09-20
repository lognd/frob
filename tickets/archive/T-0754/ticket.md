---
id: T-0754
title: 'captured Done-report claims: test-count and gate-state fields populated from
  real command output, re-verified at land'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
parent: T-0417
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
- tests/test_ticket_land.py
- tests/test_ticket_done_report_claims.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: T-0754 needs done-report/land capture+reverification tests
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_done_report_claims.py
  reason: T-0754 needs done-report/land capture+reverification tests
  actor: logan
  at: '2026-07-23'
body_changes:
- mode: append
  reason: 'T-0754 review round 2 fix #4: refresh the pre-work sweep BEFORE any

    inner check runs check_gates() (a live frob check --ticket spawn) --

    landing can pull in unrelated main-side commits that touch the

    ticket''s scope globs, moving the sweep''s scope digest out from under it

    (see _refresh_prework_sweep''s own doc, T-0236). Done AFTER that check

    instead, check_gates() would observe a stale-sweep PRE001 the Done

    report''s captured claim never carried, refusing the land on a false

    divergence.'
  actor: logan
  at: '2026-09-19'
  old_length: 1247
  new_length: 1808
- mode: append
  reason: 'T-0754: re-verify captured Done-report claims (test count, gate state)

    against the SAME post-merge tree post_merge_check just re-verified

    evidence against, before the dry-run early return so --dry-run stays a

    real guarantee. Review round 2 fix #3: the test-count half is derived

    from passing_ids (the exact set D-05''s own passed() run just computed

    above), never a second collect+run, halving the real cost of a

    run_tests-supplying land.


    T-2064/T-2076 CORRECTION: a T-2064 probe that used to sit here compared

    root''s live HEAD against root_pre_land_tip and read "equal" as proof

    the check_gates() spawn observes root''s pre-land tree via cwd=root.

    That comparison was a tautology -- root is never mutated before

    _land_squash_apply runs, so root''s HEAD is trivially unchanged here no

    matter what cwd the spawn actually uses; the "equal" reading proved

    nothing and was a false positive. T-2076 traced the real caller wiring

    (_land_core_invoke, src/frob/app/ticket_runner/_land_cmd.py) and

    confirmed directly (a probe on a real spawn, plus a fixture-repo

    reproduction) that check_gates/check_gate_findings already spawn with

    cwd=worktree -- the correctly-merged tree -- by the time this point in

    _land_locked runs. The real defect was a different silent failure mode

    entirely: frob check''s own _refuse_full_check_for_agent (T-0627)

    refuses this spawn''s unchunked shape whenever the caller''s shell

    carries FROB_AGENT (true for every dispatched worktree agent), which

    made check_gates() return None ("unmeasured") on every land run from an

    agent shell. See _shared_check_spawn_fn''s own docstring

    (src/frob/app/ticket_runner/_verify.py) for the full account and the

    fix (FROB_ALLOW_FULL_CHECK=1 in the spawn''s own child env,

    unconditionally).'
  actor: logan
  at: '2026-09-19'
  old_length: 1808
  new_length: 3873
evidence:
- tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_round_trips_through_a_done_report_body
- tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_missing_section_returns_none
- tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_omitted_when_no_callables_supplied
- tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_captured_from_real_callables
- tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_divergent_real_count_is_recorded_not_the_typed_narrative
- tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_gate_state_only_no_test_capture_leaves_claims_out
- tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_matching_claims_land_succeeds
- tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_divergent_test_count_refuses_land
- tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land
- tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_no_claims_section_skips_reverification
- tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_free_prose_elsewhere_never_masquerades_as_claims
- tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_only_lines_inside_the_claims_heading_count
- tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land
- tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_divergent_warning_or_waived_count_alone_still_lands
- tests/ticket_land_suite/test_claim_close.py::TestDoneReportThenLandRealClosuresEndToEnd::test_real_closures_done_report_then_land_succeeds
designated_repro_test: null
acceptance:
- text: GIVEN a done-report whose typed test count differs from the actual evidence
    run WHEN done-report captures THEN it records the real count and flags the divergence;
    GIVEN a captured gate-state that no longer holds at land THEN land errors
  evidence:
  - tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_round_trips_through_a_done_report_body
  - tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_missing_section_returns_none
  - tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_omitted_when_no_callables_supplied
  - tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_captured_from_real_callables
  - tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_divergent_real_count_is_recorded_not_the_typed_narrative
  - tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_gate_state_only_no_test_capture_leaves_claims_out
  - tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_matching_claims_land_succeeds
  - tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_divergent_test_count_refuses_land
  - tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land
  - tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_no_claims_section_skips_reverification
  - tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_free_prose_elsewhere_never_masquerades_as_claims
  - tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_only_lines_inside_the_claims_heading_count
  - tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land
  - tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_divergent_warning_or_waived_count_alone_still_lands
  - tests/ticket_land_suite/test_claim_close.py::TestDoneReportThenLandRealClosuresEndToEnd::test_real_closures_done_report_then_land_succeeds
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Root-cause analysis 2026-07-22: across ~15 review rejects this session, the single largest class was the Done report claiming numbers/state that did not reproduce (T-0572 142-reported-as-145 and 0-errors-that-was-27; T-0710/T-0724 undisclosed gate state; the phantom-filing family already closed by TICK006). The Done report is the ONLY pipeline artifact that is unverified free prose -- evidence ids resolve, scope binds, the diff is real, but the prose claims are typed from memory/stale runs. Fix: CAPTURE, do not type. Extend frob ticket done-report so structured claim fields are populated from REAL command output, not narrative: (1) a test-result field captured by actually running the recorded evidence node ids (pass count + a digest of the run), refusing to record a count the run did not produce; (2) a gate-state field auto-filled from a fresh frob check --ticket capture (the "clean except X" line becomes generated, never typed); (3) at land, re-verify the captured claims still hold against the merged tree and ERROR on divergence. The narrative prose stays for WHY; the CHECKABLE claims become captured artifacts. This is the general form of TICK006 (which made filing-claims checkable) applied to test-count and gate-state claims.

<!-- narrative-moved:src/frob/tickets/_land.py:2978:T-0754 -->
T-0754 review round 2 fix #4: refresh the pre-work sweep BEFORE
any inner check runs `check_gates()` (a live `frob check
--ticket` spawn) -- landing can pull in unrelated main-side
commits that touch the ticket's scope globs, moving the sweep's
scope digest out from under it (see `_refresh_prework_sweep`'s
own doc, T-0236); done AFTER that check instead, `check_gates()`
would observe a stale-sweep PRE001 the Done report's captured
claim never carried, refusing the land on a false divergence.

<!-- narrative-moved:src/frob/tickets/_land.py:3000:T-0754 -->
T-0754: re-verify captured Done-report claims (test count, gate
state) against the SAME post-merge tree `post_merge_check` just
re-verified evidence against -- same ordering rationale (before
the dry-run early return, so `--dry-run` stays a real guarantee).
T-0754 review round 2 fix #3: the test-count half is DERIVED from
`passing_ids` (the exact set D-05's own `passed()` run just
computed above), never a second collect+run -- halves the real
cost of a `run_tests`-supplying land.

T-2064/T-2076 CORRECTION: the T-2064 probe that used to sit here
compared `root`'s live HEAD against `root_pre_land_tip` and read
"equal" as proof the check_gates() spawn observes root's
PRE-land tree via `cwd=root`. That comparison is a tautology --
`root` is never mutated before `_land_squash_apply` runs (this
module's own comment, a few lines below, names it as the ONLY
step that touches `root`), so `root`'s HEAD is trivially
unchanged here NO MATTER what `cwd` the spawn actually uses; the
"equal" reading proved nothing about the spawn itself and was a
false positive. T-2076 traced the real caller wiring
(`_land_core_invoke`, src/frob/app/ticket_runner/_land_cmd.py)
and confirmed directly (a probe on a real spawn, plus a fixture-
repo reproduction) that `check_gates`/`check_gate_findings`
already spawn with `cwd=worktree` -- the correctly-merged tree
-- by the time this point in `_land_locked` runs. The real
defect was a DIFFERENT silent failure mode entirely: `frob
check`'s own `_refuse_full_check_for_agent` (T-0627) refuses
this spawn's unchunked shape whenever the caller's shell carries
`FROB_AGENT` (true for every dispatched worktree agent), which
made `check_gates()` return `None` ("unmeasured") on every land
run from an agent shell -- see `_shared_check_spawn_fn`'s own
docstring (`src/frob/app/ticket_runner/_verify.py`) for the full
account and the fix (`FROB_ALLOW_FULL_CHECK=1` in the spawn's
own child env, unconditionally).
T-2913: rapid already lets the deferred post-land sweep