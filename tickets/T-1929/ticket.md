---
id: T-1929
title: 'Confirmatory-only evidence is only detectable at land: --designate-repro validates
  nothing and BUG002 has no on-demand path'
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_mutation_evidence.py
- src/frob/gates/__init__.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/app/config.py
- docs/guides/agent-playbook.md
- docs/modules/tickets.md
- tests/unit/test_ticket_runner_designate_repro.py
- tests/gates/test_bug_repro_at_ref_public.py
- tests/test_gates_mutation_evidence.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: 'T-1929 scope: designate-time repro validation wiring + on-demand check-repro
    flag + playbook doc update'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'T-1929 scope: designate-time repro validation wiring + on-demand check-repro
    flag + playbook doc update'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'T-1929 scope: designate-time repro validation wiring + on-demand check-repro
    flag + playbook doc update'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: 'T-1929 scope: designate-time repro validation wiring + on-demand check-repro
    flag + playbook doc update'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-1929 scope: designate-time repro validation wiring + on-demand check-repro
    flag + playbook doc update'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: 'T-1929 scope: designate-time repro validation wiring + on-demand check-repro
    flag + playbook doc update'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-1929 scope: designate-time repro validation wiring + on-demand check-repro
    flag + playbook doc update'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/test_ticket_runner_designate_repro.py
  reason: 'T-1929 scope: designate-time repro validation wiring + on-demand check-repro
    flag + playbook doc update'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/gates/test_bug_repro_at_ref_public.py
  reason: 'T-1929 scope: designate-time repro validation wiring + on-demand check-repro
    flag + playbook doc update'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: 'T-1929 scope: designate-time repro validation wiring + on-demand check-repro
    flag + playbook doc update'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-1929: WIRE001 requires new AppConfig dest names (ticket_check_repro,
    ticket_designate_repro_force) copied into from_external''s field-name tuples'
  actor: logan
  at: '2026-08-09'
evidence:
- tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_refuses_passed_at_parent
- tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_refuses_no_verdict
- tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_accepts_failed_at_parent
- tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_force_overrides_loudly
- tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_non_bug_kind_skips_the_check
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_reports_failed_at_parent_exit0
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_reports_passed_at_parent_exit1
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_reports_no_verdict_exit1
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_no_node_id_resolves_designated_test
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal::test_check_repro_and_base_ref_survive_from_external
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal::test_check_repro_with_no_node_id_survives_as_empty_string
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal::test_designate_repro_force_survives_from_external
- tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_wraps_the_private_classifier
- tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_public_alias_is_the_same_enum
- tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_default_base_ref_is_main
- tests/gates/test_bug_repro_at_ref_public.py::TestDesignatedReproTestPublic::test_wraps_the_private_resolver
- tests/gates/test_bug_repro_at_ref_public.py::TestDesignatedReproTestPublic::test_falls_back_to_first_pytest_node_id
- tests/gates/test_bug_repro_at_ref_public.py::TestDesignatedReproTestPublic::test_no_evidence_is_none
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
FOUR INSTANCES IN ONE SESSION (2026-08-09): T-1907, T-1884, T-1882,
T-1911. Every one bound evidence that passed at BOTH the parent and the
fix, and every one discovered it only when `frob ticket land` refused
with EvidenceConfirmatoryOnly. T-1911 alone burned 5 land attempts
across 2 agents; T-1884 is STILL blocked on it. This is the single most
expensive recurring failure in the drain, and it is a tooling gap, not
an agent-discipline problem -- every one of those agents was explicitly
briefed on the trap and still could not detect it until land.

MEASURED, the three structural gaps:

1. `frob ticket evidence --designate-repro NODE-ID` validates NOTHING.
   src/frob/app/ticket_runner/_verify.py only SETS the designation
   (`set_designated_repro_test`). Nothing checks whether that node id
   actually fails at the parent commit. The mistake is committed at this
   exact moment and nothing says so.

2. BUG002 is not a check family. `frob check --only bug` -> "unknown
   --only stage(s) [bug]". The live families are listed in that error and
   `bug` is not among them. So an agent mid-ticket has NO on-demand way
   to ask "is my evidence confirmatory-only?"

3. It evaluates only at the END. `frob.gates.bug_repro_violations` is
   reached from src/frob/tickets/_land.py and
   src/frob/app/ticket_runner/_close_cmd.py
   (`_close_mutation_evidence_for_ticket`) -- close and land. By then the
   agent has done the whole worktree cycle: implement, test, gates, done
   report. The feedback arrives maximally far from the mistake.

Net effect: the cheapest possible check (run one test at the parent) is
deferred to the most expensive possible moment. That is backwards.

REQUIRED FIX -- make it impossible to bind confirmatory-only evidence
silently. In priority order:

A. `--designate-repro` runs the parent-commit check AT DESIGNATE TIME and
   REFUSES (non-zero, no write) when the test does not genuinely fail at
   the parent. This is the structural fix; the other two are supporting.
   Provide an explicit override flag for the rare legitimate case, and
   make the override loud and recorded, mirroring how
   `--skip-mutation-evidence` already logs.

B. Expose the same computation on demand, so an agent can check without
   mutating anything. Either a `bug` check family (`frob check --only
   bug --ticket T-####`) or a first-class read-only verb. Note `frob
   ticket reverify` already accepts `--base-ref` and
   `--skip-mutation-evidence` and may already be most of this -- ESTABLISH
   WHETHER IT ALREADY DOES THIS BEFORE BUILDING ANYTHING NEW. If it does,
   the gap is discoverability, and the fix is to surface it (and put it in
   the playbook contract), not to add a second verb. Do not duplicate
   machinery: `_close_cmd._close_mutation_evidence_for_ticket` already
   reuses `frob.gates.bug_repro_violations` through one shared entrypoint,
   and whatever you add must go through that same one.

C. THREE-WAY CLASSIFICATION, not pass/fail. This is what makes the fix
   sound rather than a new trap. The parent-commit run has three
   outcomes and they are NOT interchangeable:
     - FAILED_AT_PARENT   -> genuine repro, accept.
     - PASSED_AT_PARENT   -> confirmatory-only, refuse.
     - NO_VERDICT         -> the test could not even COLLECT at the parent
                             (pytest exit 5, e.g. it calls a function that
                             does not exist yet).
   NO_VERDICT must NEVER be treated as a pass. T-1907s original evidence
   was exactly this: the tests called a function absent at the parent, so
   the parent run collected 0 tests and "passed" vacuously. T-1882 hit the
   same shape and its agent had to hand-verify outside the gate. T-1911s
   agent explicitly confirmed its parent run was a real failure
   (collected=1 failed=1) and not a collection error -- that distinction
   is the whole ballgame and the tooling must make it, not the agent.

ACCEPTANCE
1. `--designate-repro` refuses a node id that passes at the parent, and
   refuses one that cannot collect at the parent, with distinct messages
   naming which case it is.
2. The same check is runnable on demand without mutating the ticket.
3. All three outcomes above are distinguished in the reported result;
   NO_VERDICT is never reported as acceptable.
4. Tests for all three outcomes. The PASSED_AT_PARENT and NO_VERDICT
   refusals must FAIL before the fix.
5. docs/guides/agent-playbook.md section 0 item 6 (evidence) gains the
   validate-at-designate step, so the contract every agent reads matches
   the tooling.

DO NOT weaken BUG002 anywhere in this work. It has been correct in all
four incidents; the problem is exclusively WHEN it speaks, not WHETHER
it is right.

Related but distinct, do not absorb: T-1748 (two tickets sharing one fix
mechanism cannot land from one worktree without disabling
PassengerTickets and BUG002).

## Done report

Investigated `frob ticket reverify` first, per the ticket's own instruction
to check before building anything new. It already runs
`_close_mutation_evidence_for_ticket` (the shared entrypoint into
`frob.gates.bug_repro_violations`/`mutation_evidence_violations`) with
`--base-ref`/`--skip-mutation-evidence` support -- but it REFUSES on any
ticket whose state is not already `done` (`if ticket.state is not
TicketState.DONE: sys.exit(1)`). It is a post-close send-back verb, not an
in-progress on-demand check: an agent mid-ticket (exactly the four incidents'
own situation) cannot reach it at all. The real gap was not discoverability
of an existing verb; it is a genuine missing on-demand, no-mutation path for
an in-progress ticket. Built the minimum needed, through the SAME shared
gate machinery `reverify`/`close`/`land` already use -- no second
implementation, no new check family, no new top-level verb.

Fix, in the ticket's own priority order:

A. `frob ticket evidence <id> --designate-repro NODE-ID` now runs
   `frob.gates.bug_repro_outcome_at_ref` (a new thin public wrapper around
   the existing `_bug_repro_outcome_at_ref` -- same subprocess, same
   classification, zero duplication) against the ticket's parent commit
   (`bug`/`security` kind only, mirroring BUG002's own `_ERROR_KINDS` scope)
   BEFORE writing the designation, and refuses (exit 1, no write) unless the
   outcome is FAILED_AT_PARENT. `--designate-repro-force` is the loud,
   logged (WARNING) override, same posture as `--skip-mutation-evidence`.

B. `frob ticket evidence <id> --check-repro [NODE-ID]` runs the identical
   check on demand, read-only, mutates nothing -- the answer to "is my
   evidence confirmatory-only?" available at the moment an agent is about
   to bind/designate evidence, not only at land. NODE-ID optional: falls
   back to the same resolution BUG002 itself uses (`designated_repro_test`,
   a new public wrapper around `_designated_repro_test`).

C. NO_VERDICT is a distinct, never-a-pass outcome throughout: both new
   paths report FAILED_AT_PARENT / PASSED_AT_PARENT / NO_VERDICT /
   SAME_AS_HEAD with a message naming which case fired
   (`_bug_repro_outcome_message`, shared by both A and B so the wording
   never drifts between the two call sites); only FAILED_AT_PARENT is
   accepted by either.

BUG002 itself (`bug_repro_violations`) is UNCHANGED -- same function, same
severity, same waiver, same land/close-time behavior. This only adds an
earlier, additive check at the point the mistake is actually made.

Real, non-mocked smoke test (not just the mocked unit tests): built a
throwaway git repo with a genuine off-by-one bug and fix commit, created a
`bug`-kind ticket in it, and drove the real CLI (no monkeypatching) through
all five cases against a real `git worktree add` + real pytest subprocess:
FAILED_AT_PARENT accepted by both --check-repro and --designate-repro;
PASSED_AT_PARENT refused by both; NO_VERDICT refused by --check-repro (a
test absent at the parent, pytest exit 4/5); --designate-repro-force
overrode a PASSED_AT_PARENT refusal loudly. All five matched the documented
contract exactly.

Also wired `ticket_check_repro`/`ticket_designate_repro_force` into
`AppConfig.from_external`'s allowlist (WIRE001 caught the omission --
T-1422's shape, argparse parses the dest but `from_external` silently drops
it before `AppConfig(**d)` otherwise) and added `--base-ref` to the
`evidence` subcommand (it had none before this ticket; `--designate-repro`/
`--check-repro` need one to diff against something other than the AppConfig
default of "main").

Cut: `--accepts N` binding was not usable -- this ticket's own ACCEPTANCE
section is prose, not a structured `--acceptance`-flag list
(`frob ticket show T-1929` reports "ticket has 0 acceptance item(s))"), so
`--accepts` refuses with `AcceptanceIndexOutOfRange` for any index. Evidence
is bound to the flat list instead (18 ids covering all 4 testable
acceptance criteria; criterion 5 is the docs change itself, no test
surface).

Filed: none -- no out-of-scope work discovered.

### Changed
```
 docs/guides/agent-playbook.md                    |  20 ++
 src/frob/_cli_parsers/_ticket/_closeout.py       |  40 +++
 src/frob/app/_config_external.py                 |   4 +
 src/frob/app/config.py                           |  23 ++
 src/frob/app/ticket_runner/_verify.py            | 235 +++++++++++++-
 src/frob/gates/__init__.py                       |  10 +-
 src/frob/gates/_mutation_evidence.py             |  59 +++-
 tests/gates/test_bug_repro_at_ref_public.py      |  83 +++++
 tests/unit/test_ticket_runner_designate_repro.py | 393 +++++++++++++++++++++++
 tickets/T-1929/done-report.md                    | 112 +++++++
 tickets/T-1929/ticket.md                         | 100 +++++-
 11 files changed, 1067 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_refuses_passed_at_parent` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_refuses_no_verdict` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_accepts_failed_at_parent` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_force_overrides_loudly` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_non_bug_kind_skips_the_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_reports_failed_at_parent_exit0` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_reports_passed_at_parent_exit1` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_reports_no_verdict_exit1` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_no_node_id_resolves_designated_test` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal::test_check_repro_and_base_ref_survive_from_external` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal::test_check_repro_with_no_node_id_survives_as_empty_string` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal::test_designate_repro_force_survives_from_external` (pytest node id, verified passing when recorded)
- `tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_wraps_the_private_classifier` (pytest node id, verified passing when recorded)
- `tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_public_alias_is_the_same_enum` (pytest node id, verified passing when recorded)
- `tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_default_base_ref_is_main` (pytest node id, verified passing when recorded)
- `tests/gates/test_bug_repro_at_ref_public.py::TestDesignatedReproTestPublic::test_wraps_the_private_resolver` (pytest node id, verified passing when recorded)
- `tests/gates/test_bug_repro_at_ref_public.py::TestDesignatedReproTestPublic::test_falls_back_to_first_pytest_node_id` (pytest node id, verified passing when recorded)
- `tests/gates/test_bug_repro_at_ref_public.py::TestDesignatedReproTestPublic::test_no_evidence_is_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 18 passed (from 18 evidence id(s))
- gates: 7 error(s), 1699 warning(s), 699 waived
- error-findings: COV003@tickets/T-1872, COV003@tickets/T-1895, COV003@tickets/T-1896, COV003@tickets/T-1900, COV003@tickets/T-1906, F401@/home/logan/projects/frob/.claude/worktrees/repro-validate/src/frob/gates/_fix_engine_sync.py, PRE001@tickets/T-1929
