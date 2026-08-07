---
id: T-1727
title: 'Close-time mutation-evidence sweep has no budget: 10 consecutive 540s timeouts,
  and its cost structure rewards binding weak evidence'
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_mutation_evidence.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/tickets/_evidence.py
- docs/modules/gates.md
- src/frob/tickets/_mutation_evidence.py
- src/frob/mutate/__init__.py
- tests/test_tickets_mutation_evidence.py
- tests/gates/test_mutation_evidence_err_branches.py
- docs/modules/mutate.md
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_mutation_evidence.py
  reason: 'T-1727''s declared scope names src/frob/gates/_mutation_evidence.py (the

    TEST016 Violation-producing gate wrapper), but the actual sweep engine

    that walks files/mutants and has no budget is a DIFFERENT, same-named

    file in a different package: src/frob/tickets/_mutation_evidence.py

    (check_ticket_mutation_evidence, _mutation_evidence_for_file) plus

    src/frob/mutate/__init__.py (run_mutations, _run_mutants -- the actual

    per-mutant subprocess loop). The requirements (budget the sweep,

    UNMEASURED on exceeding it, progress reporting per mutant) can only be

    implemented where the loop actually lives. Adding these two files so

    the fix lands where the defect is, not just at the wrapper that

    consumes its output.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/mutate/__init__.py
  reason: 'T-1727''s declared scope names src/frob/gates/_mutation_evidence.py (the

    TEST016 Violation-producing gate wrapper), but the actual sweep engine

    that walks files/mutants and has no budget is a DIFFERENT, same-named

    file in a different package: src/frob/tickets/_mutation_evidence.py

    (check_ticket_mutation_evidence, _mutation_evidence_for_file) plus

    src/frob/mutate/__init__.py (run_mutations, _run_mutants -- the actual

    per-mutant subprocess loop). The requirements (budget the sweep,

    UNMEASURED on exceeding it, progress reporting per mutant) can only be

    implemented where the loop actually lives. Adding these two files so

    the fix lands where the defect is, not just at the wrapper that

    consumes its output.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_tickets_mutation_evidence.py
  reason: 'T-1727''s declared scope names src/frob/gates/_mutation_evidence.py (the

    TEST016 Violation-producing gate wrapper), but the actual sweep engine

    that walks files/mutants and has no budget is a DIFFERENT, same-named

    file in a different package: src/frob/tickets/_mutation_evidence.py

    (check_ticket_mutation_evidence, _mutation_evidence_for_file) plus

    src/frob/mutate/__init__.py (run_mutations, _run_mutants -- the actual

    per-mutant subprocess loop). The requirements (budget the sweep,

    UNMEASURED on exceeding it, progress reporting per mutant) can only be

    implemented where the loop actually lives. Adding these two files so

    the fix lands where the defect is, not just at the wrapper that

    consumes its output.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/gates/test_mutation_evidence_err_branches.py
  reason: 'T-1727''s declared scope names src/frob/gates/_mutation_evidence.py (the

    TEST016 Violation-producing gate wrapper), but the actual sweep engine

    that walks files/mutants and has no budget is a DIFFERENT, same-named

    file in a different package: src/frob/tickets/_mutation_evidence.py

    (check_ticket_mutation_evidence, _mutation_evidence_for_file) plus

    src/frob/mutate/__init__.py (run_mutations, _run_mutants -- the actual

    per-mutant subprocess loop). The requirements (budget the sweep,

    UNMEASURED on exceeding it, progress reporting per mutant) can only be

    implemented where the loop actually lives. Adding these two files so

    the fix lands where the defect is, not just at the wrapper that

    consumes its output.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/mutate.md
  reason: 'T-1727''s declared scope names src/frob/gates/_mutation_evidence.py (the

    TEST016 Violation-producing gate wrapper), but the actual sweep engine

    that walks files/mutants and has no budget is a DIFFERENT, same-named

    file in a different package: src/frob/tickets/_mutation_evidence.py

    (check_ticket_mutation_evidence, _mutation_evidence_for_file) plus

    src/frob/mutate/__init__.py (run_mutations, _run_mutants -- the actual

    per-mutant subprocess loop). The requirements (budget the sweep,

    UNMEASURED on exceeding it, progress reporting per mutant) can only be

    implemented where the loop actually lives. Adding these two files so

    the fix lands where the defect is, not just at the wrapper that

    consumes its output.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/tickets.md
  reason: the real TEST016/check_ticket_mutation_evidence doc anchor (frob:describes
    edges) lives in docs/modules/tickets.md, not gates.md alone -- must update in
    the same change since this ticket changes that function's behavior (sweep_budget_s,
    unmeasured findings, bind-time warning)
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_zero_budget_reports_unmeasured_not_confirmatory
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_mid_sweep_deadline_truncates_and_reports_unmeasured
- tests/test_tickets_mutation_evidence.py::TestWarnBindTimeMutationSweepCost::test_warns_when_projected_cost_exceeds_budget
- tests/test_tickets_mutation_evidence.py::TestWarnBindTimeMutationSweepCost::test_no_warning_when_no_touched_python_files
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_real_subprocess_spawning_evidence_stays_bounded_not_hung
designated_repro_test: null
threat: null
component: null
---
`frob ticket close` timed out TEN CONSECUTIVE TIMES at 540s each on
T-1672 -- roughly 90 minutes of an agent's budget spent producing no
result at all. The agent escaped only by unbinding its own strongest
evidence and then using `--skip-mutation-evidence`.

Cause: the close-time mutation-evidence sweep re-runs every bound
evidence test ONCE PER MUTANT. Cost is O(mutants x test wall-clock), so a
test that spawns real subprocesses is pathological, and under concurrent
load from other agents it degrades further. T-1672's evidence included
`TestSpawnWithWatchdog` tests that fork real processes and sleep -- by
construction, since the ticket is a subprocess watchdog and honest
evidence for it has to spawn subprocesses.

The agent judged this "a known, disclosed mechanism working as designed"
and did not file. It is not: 90 minutes of no-result is a structural
defect regardless of whether each individual step behaves as documented.

THE PERVERSE INCENTIVE IS THE REAL BUG. The escape the agent found was to
UNBIND ITS THREE SLOWEST TESTS. Those were the tests that actually
exercised the watchdog. The cost structure therefore pushes every agent
toward binding cheap, shallow evidence and away from the expensive tests
that prove the hard part -- exactly inverting what evidence binding
exists to achieve. A gate that makes good evidence expensive and bad
evidence free will get bad evidence, reliably, and it will look clean
doing it.

Required:

1. BUDGET THE SWEEP, and make exceeding it UNMEASURED -- not pass, not
   fail. Today it simply runs until the caller's timeout, so the caller
   cannot distinguish "still working" from "wedged", and gets neither an
   answer nor a reason. On exceeding budget: stop, report which evidence
   ids were measured and which were not, and require the existing
   `--skip-mutation-evidence` justification for the remainder. "Could not
   measure" must never render as "verified" (T-1703's lesson, same shape).
2. WARN AT BIND TIME, NOT CLOSE TIME. `frob ticket evidence` knows the
   node ids it is binding and can time a single run. If a bound test's
   wall-clock times the expected mutant count exceeds the budget, say so
   WHEN IT IS BOUND -- naming the test and the projected close cost --
   rather than at close, an hour of work later, when unbinding it means
   weakening the ticket.
3. REPORT PROGRESS WHILE RUNNING. Emit per-mutant/per-test progress so a
   long sweep is visibly working. Ten silent 540s timeouts is the
   worst possible feedback: indistinguishable from a hang, and the agent
   correctly could not tell which it was.
4. DO NOT simply raise the timeout. The cost is multiplicative in mutants
   x test time; a bigger constant postpones the same wall.

Worth considering while here, but do not let it displace the above: cap
or sample the mutant set for expensive tests, and/or run mutants
concurrently. Both change what the gate measures, so state explicitly
what coverage is being traded away rather than quietly reducing it.

Evidence for this ticket must include the actual pathological shape -- a
bound evidence test that spawns a subprocess -- and assert that close
returns a BOUNDED, EXPLICIT unmeasured result rather than hanging.