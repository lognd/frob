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
