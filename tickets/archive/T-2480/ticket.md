---
id: T-2480
title: check-repro's fixed 60s budget turns a slow but valid repro test into an indistinguishable
  NO_VERDICT
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/gates/_mutation_evidence.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- docs/modules/tickets.md
- docs/modules/tickets-landing.md
- src/frob/app/config.py
- src/frob/app/_config_external.py
- tests/gates/test_bug_repro_at_ref_public.py
- tests/test_gates_mutation_evidence.py
- tests/unit/test_ticket_runner_designate_repro.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: the actual repro-timeout classification (_BugReproOutcome, _run_designated_test)
    lives in gates/_mutation_evidence.py and the --check-repro/--designate-repro CLI-facing
    messaging lives in app/ticket_runner/_verify.py, not in tickets/_evidence.py as
    originally scoped; a --repro-timeout-s override needs a new CLI flag in _cli_parsers/_ticket/_closeout.py
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: the actual repro-timeout classification (_BugReproOutcome, _run_designated_test)
    lives in gates/_mutation_evidence.py and the --check-repro/--designate-repro CLI-facing
    messaging lives in app/ticket_runner/_verify.py, not in tickets/_evidence.py as
    originally scoped; a --repro-timeout-s override needs a new CLI flag in _cli_parsers/_ticket/_closeout.py
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: the actual repro-timeout classification (_BugReproOutcome, _run_designated_test)
    lives in gates/_mutation_evidence.py and the --check-repro/--designate-repro CLI-facing
    messaging lives in app/ticket_runner/_verify.py, not in tickets/_evidence.py as
    originally scoped; a --repro-timeout-s override needs a new CLI flag in _cli_parsers/_ticket/_closeout.py
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets.md
  reason: bug_repro_outcome_at_ref/designated_repro_test's frob:doc anchors both live
    here and need the new TIMEOUT outcome + --repro-timeout-s documented
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: _BugReproOutcome's frob:doc anchor lives here; adding TIMEOUT needs it touched
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/config.py
  reason: the new --repro-timeout-s flag needs a ticket_repro_timeout_s field declared
    on AppConfig (pydantic BaseModel, fields must be declared) alongside the existing
    ticket_check_repro/ticket_designate_repro_force fields
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/_config_external.py
  reason: AppConfig.from_external's field-name allowlist in _config_external.py must
    carry ticket_repro_timeout_s through or the new flag is silently dropped (WIRE001
    caught it); the three test files hold this ticket's positive-control/regression
    evidence
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/gates/test_bug_repro_at_ref_public.py
  reason: AppConfig.from_external's field-name allowlist in _config_external.py must
    carry ticket_repro_timeout_s through or the new flag is silently dropped (WIRE001
    caught it); the three test files hold this ticket's positive-control/regression
    evidence
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: AppConfig.from_external's field-name allowlist in _config_external.py must
    carry ticket_repro_timeout_s through or the new flag is silently dropped (WIRE001
    caught it); the three test files hold this ticket's positive-control/regression
    evidence
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_ticket_runner_designate_repro.py
  reason: AppConfig.from_external's field-name allowlist in _config_external.py must
    carry ticket_repro_timeout_s through or the new flag is silently dropped (WIRE001
    caught it); the three test files hold this ticket's positive-control/regression
    evidence
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_slow_test_exceeding_budget_is_timeout_not_no_verdict
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_timeout_outcome_reports_distinctly_and_exits_nonzero
- tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_failing_test_still_refused
- tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_reproducing_test_completes_normally
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_repro_timeout_s_is_forwarded
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal::test_repro_timeout_s_survives_from_external
designated_repro_test: null
acceptance:
- text: Given a repro test that exceeds the check-repro time budget, when it is checked,
    then the result reports a timeout distinctly from a test that ran and did not
    reproduce.
  evidence:
  - tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_slow_test_exceeding_budget_is_timeout_not_no_verdict
  - tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_timeout_outcome_reports_distinctly_and_exits_nonzero
  - tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_repro_timeout_s_is_forwarded
  - tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal::test_repro_timeout_s_survives_from_external
- text: Given a fast test that genuinely does not fail at the parent commit, when
    it is checked, then it is still rejected, proving BUG002's real check was not
    weakened.
  evidence:
  - tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_failing_test_still_refused
- text: Given a fast genuinely-reproducing test, when it is checked, then it verifies
    through the normal path with no added friction.
  evidence:
  - tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_reproducing_test_completes_normally
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: 472bff74eb1b5784576a66e625b765a18721b7d3
---
`frob ticket evidence --check-repro` / `--designate-repro` runs the
candidate repro test in a subprocess under a FIXED 60s budget
(`_BUG_REPRO_TIMEOUT_S`). A test that legitimately takes longer returns
`NO_VERDICT`, which reads as "reproduction could not be demonstrated"
-- indistinguishable, to a reader, from a genuinely confirmatory-only
test that the gate is right to reject.

MEASURED instance (T-2463): the designated repro loads and elaborates
the FULL strata design plus the entire SYS gate, which exceeds 60s on
this machine. The agent verified the fail-at-parent / pass-at-fix shape
BY HAND instead -- committed the test alone, confirmed it FAILED with 5
unexpected SYS violations against the unfixed strata file, restored the
fix, confirmed it passed -- and then used `--designate-repro-force`
with that transcript as the recorded reason.

That was the correct handling and the disclosure was complete. But note
what the workflow required: a correct, genuinely-reproducing test forced
the agent onto the FORCE path, which is the same escape hatch used when
a repro truly cannot be demonstrated. The audit trail now cannot
distinguish "forced because the tool timed out on a slow but valid
test" from "forced because no reproduction exists", except by reading
the free-text reason. Every additional legitimate use of `--force`
erodes the signal that `--force` was meant to carry.

WHY THE TIMEOUT IS THE WRONG SHAPE HERE. Repro tests for
architecture/design-level defects are inherently slow, because
demonstrating the defect means elaborating the whole model. So the
tests most likely to exceed the budget are precisely the ones covering
the broadest, highest-consequence defects. A fixed 60s ceiling
selectively disenfranchises the most valuable repro tests.

Also relevant: this repo has just spent significant effort establishing
that a budget which DROPS work while reporting a clean-looking result
is a false-green generator (T-2456: the land check's 300s budget was
silently dropping an entire stage group from every sweep). This is the
same shape at a smaller scale -- a fixed budget converting "did not
finish" into a verdict.

FIX SHAPE:
  - `NO_VERDICT` due to TIMEOUT must be reported distinctly from
    `NO_VERDICT` due to the test not reproducing. They are different
    facts and only one of them is evidence about the ticket. This is
    the fail-loudly doctrine (T-2391) applied to the repro checker:
    "could not measure" is not "measured and found nothing".
  - Make the budget configurable, and/or scale it -- a per-invocation
    override, or a longer default for tests the caller marks as
    design-level. Do not simply raise the constant and leave the same
    cliff further out.
  - Consider whether a timeout should auto-permit the force path with
    the timeout recorded as the structured reason, so the audit trail
    distinguishes the two cases mechanically rather than by prose.

POSITIVE CONTROLS:
  - must-distinguish: a test that exceeds the budget reports a TIMEOUT
    outcome, not a bare NO_VERDICT.
  - must-still-refuse: a fast test that genuinely does NOT fail at the
    parent commit is still rejected. Do not fix the timeout by
    weakening BUG002's actual check, which has caught real
    confirmatory-only evidence repeatedly.
  - must-still-complete: a fast, genuinely-reproducing test still
    verifies within the normal path with no added friction.