---
id: T-3104
title: 'BUG002 cannot verify environment-absence bugs: the sandbox always has the
  thing whose absence is the defect'
state: in-progress
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_bug_repro.py
- tests/test_gates_mutation_evidence.py
- tests/gates/test_bug_repro_at_ref_public.py
- tests/gates/test_env_absent_bug002_repro.py
- docs/modules/gates.md
- docs/modules/tickets.md
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: T-3104's own bound evidence lives in these three test files
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/gates/test_bug_repro_at_ref_public.py
  reason: T-3104's own bound evidence lives in these three test files
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/gates/test_env_absent_bug002_repro.py
  reason: T-3104's own bound evidence lives in these three test files
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/gates.md
  reason: 'AFFECT001: bug_repro_violations/_BugReproOutcome/bug_repro_outcome_at_ref/designated_repro_test/must_still_pass_violations
    changed and their affects()-closure docs need the new frob:env-absent/frob:env-absent-unverifiable
    directives documented'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/tickets.md
  reason: 'AFFECT001: bug_repro_violations/_BugReproOutcome/bug_repro_outcome_at_ref/designated_repro_test/must_still_pass_violations
    changed and their affects()-closure docs need the new frob:env-absent/frob:env-absent-unverifiable
    directives documented'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'AFFECT001: bug_repro_violations/_BugReproOutcome/bug_repro_outcome_at_ref/designated_repro_test/must_still_pass_violations
    changed and their affects()-closure docs need the new frob:env-absent/frob:env-absent-unverifiable
    directives documented'
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: set
  reason: Record the verification gap surfaced by T-3075's forced BUG002/TEST016 waiver,
    with the UNVERIFIABLE-IN-SANDBOX third-state requirement
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3842
evidence:
- tests/test_gates_mutation_evidence.py::TestEnvAbsent::test_single_directive_extracted
- tests/test_gates_mutation_evidence.py::TestEnvAbsent::test_comma_separated_names_extracted_in_order
- tests/test_gates_mutation_evidence.py::TestEnvAbsent::test_no_directive_is_empty
- tests/test_gates_mutation_evidence.py::TestEnvAbsent::test_duplicate_names_deduplicated_first_wins
- tests/test_gates_mutation_evidence.py::TestEnvAbsentUnverifiable::test_reason_present_recognized
- tests/test_gates_mutation_evidence.py::TestEnvAbsentUnverifiable::test_bare_directive_without_reason_not_recognized
- tests/test_gates_mutation_evidence.py::TestEnvAbsentUnverifiableOutcome::test_unverifiable_directive_short_circuits_before_repro_run
- tests/gates/test_env_absent_bug002_repro.py::TestEnvAbsentBug002Repro::test_env_absent_kwarg_reproduces_identity_absence_defect_at_parent
- tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_wraps_the_private_classifier
- tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_default_base_ref_is_main
designated_repro_test: tests/gates/test_env_absent_bug002_repro.py::TestEnvAbsentBug002Repro::test_env_absent_kwarg_reproduces_identity_absence_defect_at_parent
evidence_changes:
- old_node: tests/test_gates_mutation_evidence.py::TestEnvAbsentRepro::test_env_absent_directive_makes_identity_absence_defect_reproduce
  new_node: tests/gates/test_env_absent_bug002_repro.py::TestEnvAbsentBug002Repro::test_env_absent_kwarg_reproduces_identity_absence_defect_at_parent
  reason: moved to a dedicated repro-shaped file so the designated repro test's parent-commit
    failure is a clean TypeError, not a whole-module import error
  actor: logan
  at: '2026-08-27'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FOUND 2026-08-27 while landing T-3075 (five tests that read ambient developer
state and so passed locally but failed in CI). The fix was hermetic and
verified both directions. But the ticket could not close through the normal
path: BUG002 (the close-time repro check) and TEST016 (mutation evidence) both
had to be waived, because THIS REPO'S OWN VERIFICATION SANDBOX HAS REAL GIT
IDENTITY.

The defect being fixed was "the test breaks when git identity is ABSENT". The
gate that verifies a bug fix runs in an environment where identity is always
PRESENT. So the repro cannot fail at the parent commit inside the sandbox, and
BUG002 -- which exists precisely to prove a regression test genuinely
reproduces the bug -- cannot do its job. The agent verified the fix by hand
against a simulated no-identity HOME instead, and waived the gate with a stated
reason.

THE SHAPE OF THE GAP. frob's verification machinery can reproduce a bug that is
a function of THE CODE. It cannot reproduce a bug that is a function of THE
ENVIRONMENT'S ABSENCE -- a missing global git identity, an empty or absent
`~/.claude`, an unset environment variable, a missing binary on PATH, a
platform lacking a POSIX primitive. For that whole class, the gate is
structurally unable to verify, so every such fix must be waived through.

WHY THAT IS WORSE THAN IT SOUNDS. This is exactly the class of bug that CI
finds and local runs do not, which makes it the class most likely to reach
main unnoticed -- and it is the class for which our strongest verification gate
is inert. T-3075's own five tests are the proof: they were green on the
developer's machine for as long as they existed and only surfaced when CI
first reached the Test step. Waiving BUG002 for them is correct in the moment
and corrosive as a habit; this repo already measured 2117 `frob:waive` uses
against 85 `frob:debt`, and "the gate could not check this" is precisely how a
waiver population grows.

WHAT IS WANTED. A way to express, and then actually VERIFY, "this test must
also hold under environment X-absent". Some possibilities, none prescribed:
  - a repro that declares the environmental precondition it needs REMOVED
    (no git identity / empty HOME / unset VAR), which the sandbox then honours
    when running the parent-commit check;
  - a hermeticity marker on tests that must pass under a stripped environment,
    checked in CI as a distinct job rather than inside the ordinary sandbox;
  - at minimum: BUG002 recognising that a repro is environment-conditioned and
    reporting UNVERIFIABLE-IN-SANDBOX as a distinct outcome rather than
    requiring a blanket waiver. That third state matters -- this repo's standing
    doctrine is that UNRESOLVED is never counted as either pass or fail
    (T-1664), and a waiver currently collapses it to "pass".

RELATED, DO NOT DUPLICATE: T-3075 (the five tests, landed
`fb81130b34373a5fd805c2d5084840ba07ca6d65`) is the instance. T-2916 owns
frob's silent platform degradation, which is the same environment-absence
problem viewed from the portability side. This ticket is about the VERIFICATION
gap, not about either fix.

ACCEPTANCE
- An environment-conditioned repro can be expressed and verified without
  waiving BUG002. Demonstrate on T-3075's own case: the identity-absence repro
  must be shown failing at the parent commit through the tooling, not by hand.
- Must-stay-quiet: an ordinary code-only repro is unaffected and still verifies
  exactly as it does today.
- If full verification is not achievable, BUG002 at minimum reports
  UNVERIFIABLE-IN-SANDBOX as its own outcome, distinct from both verified and
  waived, and that outcome is visible in the ledger rather than absorbed into a
  waiver.
- Report how many existing waivers in the repo are of this
  "gate could not check this" shape, so the size of the class is known.
