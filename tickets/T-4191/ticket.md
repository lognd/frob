---
id: T-4191
title: 'CI red on WIRE002: a private test fixture''s WIRE001 waiver needs a follow-up
  ticket for wiring that will never happen'
state: done
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_flag_coverage_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_must_now_fire_reports_the_genuinely_dropped_flag
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_must_still_pass_when_everything_is_forwarded
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_this_repos_own_frob_toml_reports_zero
- tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo
- tests/gates_suite/test_wire.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_missing
designated_repro_test: tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo
acceptance:
- text: given the live-repo WIRE002 assertion, when the suite runs, then it passes
  evidence:
  - tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo
- text: given a WIRE001 waiver on a production symbol with no follow-up attribute,
    when the gate runs, then it is still refused
  evidence:
  - tests/gates_suite/test_wire.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_missing
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI IS RED ON ONE TEST, AND THE FIX IS ONE ATTRIBUTE -- BUT THE REASON IT IS RED IS
A THIRD INSTANCE OF A PATTERN ALREADY FILED TWICE.

THE FAILURE, ubuntu leg:

    tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo
    WIRE002: frob:waive WIRE001 at tests/unit/test_flag_coverage_gate.py
    ::_sync_fixture_project is missing a follow_up="T-####" attribute --
    a WIRE001 waiver must bind to a real, open follow-up ticket

T-4171 added a private test fixture helper and waived WIRE001 on it. The waiver
carries a reason but no follow-up attribute, and WIRE002 requires one.

I TRACED WHY THE WAIVER WAS ADDED AT ALL, and the agent's stated justification is
wrong in an instructive way. Its reason says the helper is "the same shape as
_write_fixture_project immediately below it". That neighbour carries NO WAIVER --
because it is not NEW. WIRE001 is diff-scoped: it asks whether the symbol THIS
DIFF ADDED has a caller outside the diff's own test files. The new helper IS
called, twice, by tests in its own file -- but test callers do not count, so
WIRE001 fires on the new one and never fired on the pre-existing one. The
asymmetry is age, not shape.

SO THE WAIVER IS LEGITIMATE AND THE FOLLOW-UP REQUIREMENT IS THE PROBLEM. A
private per-file test fixture will never be "wired" to production code -- that is
what makes it a fixture. Demanding a follow-up ticket for it means filing a ticket
that can never be worked and will be dropped, which is the third time this drive
that a rule can be cleared only by manufacturing a queue entry:

    T-4141  close refuses a Done report saying "no follow-up is needed", so
            declaring that nothing needs filing reads as failing to file
    F-355   a waiver could not cite the ticket it sits on, so an agent filed a
            throwaway ticket purely to have a citable id
    this    a private test fixture must name a follow-up ticket for wiring that
            will never happen

Individually each is small. Together they are a queue that accumulates tickets
filed to satisfy gates, which costs the queue the property that makes it worth
reading.

THE IMMEDIATE FIX, and it is honest rather than a workaround: point the follow-up
at T-4151. That ticket owns the WIRE001 mechanism and records, from four consumer
reports, that the gate answers a call-reachability question with a text scan and
cannot see real callers. A waiver that exists BECAUSE the gate cannot see
test-internal callers legitimately binds to the ticket that would remove the need
for it. Do not invent a new ticket for this.

THEN RECORD THE CLASS OBSERVATION ON T-4151 rather than filing a fourth ticket
about junk follow-ups: WIRE002's follow-up requirement is correct for a production
symbol awaiting wiring and wrong for a private test fixture, and the gate cannot
currently tell them apart. That is a scoping question for the rule, and T-4151 is
already the place where WIRE001's subject is being reconsidered.

DO NOT FIX THIS BY DELETING THE WAIVER. WIRE001 fires legitimately here by its own
stated contract; removing the waiver would just move the failure from WIRE002 to
WIRE001.

MUST-FIRE FIXTURE:   the live-repo WIRE002 assertion passes.
MUST-STAY-QUIET:     a WIRE001 waiver on a PRODUCTION symbol with no follow-up is
                     still refused -- the requirement is right for its real
                     subject and must not be weakened to fix the fixture case.

ACCEPTANCE
- The waiver carries a follow-up naming T-4151, not a newly invented ticket.
- The live-repo WIRE002 test passes.
- The production-symbol case proven still refused.
- The fixture-versus-production scoping question recorded on T-4151.