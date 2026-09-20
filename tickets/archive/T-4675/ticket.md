---
id: T-4675
title: 'SF-07: overdue assumes are documented as gate failures and are not -- wire
  the verdict before the 2026-10-15 cliff'
state: done
kind: bug
origin: agent
created: '2026-09-19'
priority: critical
parent: T-4666
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_claims.py
- docs/strata/evidence.md
- docs/strata/charter.md
- tests/unit/strata/test_claims_overdue.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/_models.py
  reason: T-3964 holds active lease on _models.py; cannot touch, per BRIEF do-not-touch-leased-elsewhere
    rule
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/strata/test_claims_overdue.py::TestFutureAssumeStaysAssumed::test_future_review_stays_assumed_no_finding
- tests/unit/strata/test_claims_overdue.py::TestFutureAssumeStaysAssumed::test_the_real_shared_cliff_date_is_still_future_at_the_fixed_today
- tests/unit/strata/test_claims_overdue.py::TestOverdueAssumeIsAGateFinding::test_overdue_review_yields_refuted_finding
- tests/unit/strata/test_claims_overdue.py::TestOverdueAssumeIsAGateFinding::test_overdue_review_logs_warning_with_owner_and_date
designated_repro_test: null
acceptance:
- text: Given _models.py:589, docs/strata/evidence.md:117 and docs/strata/charter.md:4
    all state overdue assumes are gate failures while _claims.py:654-655 only calls
    _log.warning and returns Verdict.ASSUMED, when this lands, then a test constructing
    an assume with a past review date asserts the evaluation yields a gate FINDING
    -- a positive control that fails at HEAD c8f56ef10.
  evidence:
  - tests/unit/strata/test_claims_overdue.py::TestFutureAssumeStaysAssumed::test_future_review_stays_assumed_no_finding
  - tests/unit/strata/test_claims_overdue.py::TestFutureAssumeStaysAssumed::test_the_real_shared_cliff_date_is_still_future_at_the_fixed_today
  - tests/unit/strata/test_claims_overdue.py::TestOverdueAssumeIsAGateFinding::test_overdue_review_yields_refuted_finding
  - tests/unit/strata/test_claims_overdue.py::TestOverdueAssumeIsAGateFinding::test_overdue_review_logs_warning_with_owner_and_date
- text: Given all 33 assumes in design/frob.strata carry review 2026-10-15 and must
    stay green until then, when the gate evaluates a FUTURE review date, then a test
    asserts it still yields ASSUMED with no finding (negative control), and a third
    test pins a fixed today so neither can pass merely because a real date drifted.
  evidence:
  - tests/unit/strata/test_claims_overdue.py::TestFutureAssumeStaysAssumed::test_future_review_stays_assumed_no_finding
  - tests/unit/strata/test_claims_overdue.py::TestFutureAssumeStaysAssumed::test_the_real_shared_cliff_date_is_still_future_at_the_fixed_today
- text: Given docs/strata/charter.md:4's INV003 waiver reason asserts this gap exists,
    when this lands, then that reason plus docs/strata/evidence.md:117 plus the _models.py:589
    comment all agree with the implementation in the SAME change.
  evidence:
  - tests/unit/strata/test_claims_overdue.py::TestOverdueAssumeIsAGateFinding::test_overdue_review_yields_refuted_finding
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
SF-07 (HIGH). Leaf of story C (T-4666) under epic T-4662. Story points: 2.
IMMEDIATELY DISPATCHABLE -- no blockers.

EVIDENCE, every line re-verified by the planner at HEAD c8f56ef10:
- src/frob/strata/_models.py:589
    review: str | None = None  # ISO date; overdue assumes are gate failures
- docs/strata/evidence.md:117
    "an overdue review date is a gate failure"
- src/frob/strata/_claims.py:654-655, inside `_eval_assumed`, is the ENTIRE
  enforcement:
    _log.warning("assume %s review overdue (%s)", claim.id, claim.review)
    detail += f"; review overdue since {claim.review}"
  and the function returns Verdict.ASSUMED. Nothing converts that into a
  Violation. `git grep overdue -- src/frob` returns ONLY those two lines.
- docs/strata/charter.md:4 already concedes it, inside an INV003 waiver reason:
  "Law 3's 'overdue assumptions are gate failures' specifically is NOT yet wired
  into frob check (evaluate_claims flags an overdue assume in its detail text
  but stays verdict=ASSUMED, not a gate error) -- that gap is real design debt,
  not something to falsely bind as proven".

THE CLIFF. All 33 assumes in design/frob.strata carry review "2026-10-15". On
2026-10-16 the TCB of frob's own security model silently expires AND THE GATE
STAYS GREEN. That is 26 days from the audit date (2026-09-19). This is the
reason story C is not deferred behind the owner's grammar rethink: wiring a
verdict that three separate artifacts already claim exists is closing the gap
between the code and its own comment, not a semantics change.

NOT A PROBLEM TODAY (from the audit's "found NO friction" section, so nobody
chases it): no assume is currently overdue -- all 33 dates are in the future as
of 2026-09-19 -- and all 33 carry `owner logan`, so _compliance.py:456's
"assumed with no owner/review date" path has no current trigger. The bug is the
UNENFORCED VERDICT and the cliff, not a live overdue claim.

WHAT TO BUILD
Convert an overdue review in _eval_assumed into a real gate finding, and make
docs/strata/evidence.md, docs/strata/charter.md (its waiver reason now becomes
false and must be corrected or removed) and the _models.py:589 comment all agree
with the implementation in the SAME change. Log the claim id, its review date
and the evaluation date at WARNING on every overdue claim, and at INFO the count
of assumes within N days of expiry -- 33 claims sharing one date means the next
cliff is a fleet-wide event that deserves advance warning.

POSITIVE CONTROL (the test that fails today)
A test constructing an assume whose review date is in the past and asserting the
evaluation yields a gate FINDING (not Verdict.ASSUMED with a warning). It fails
at HEAD. Add a second test pinning a fixed "today" so it can never pass merely
because a real date drifted, and a third asserting a FUTURE review date still
yields ASSUMED with no finding (the negative control -- this must not start
failing all 33 of frob's own assumes before 2026-10-15).