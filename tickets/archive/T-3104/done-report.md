## Done report

Changed:
- src/frob/gates/_bug_repro.py::_ENV_ABSENT_RE
- src/frob/gates/_bug_repro.py::_ENV_ABSENT_UNVERIFIABLE_RE
- src/frob/gates/_bug_repro.py::_BugReproOutcome.ENV_ABSENCE_UNVERIFIABLE
- src/frob/gates/_bug_repro.py::_env_absent_vars
- src/frob/gates/_bug_repro.py::_env_absent_unverifiable_reason
- src/frob/gates/_bug_repro.py::_spawn_designated_test (env_absent kwarg)
- src/frob/gates/_bug_repro.py::_run_designated_test (env_absent kwarg)
- src/frob/gates/_bug_repro.py::_bug_repro_outcome_at_ref (env_absent kwarg)
- src/frob/gates/_bug_repro.py::bug_repro_outcome_at_ref (env_absent kwarg)
- src/frob/gates/_bug_repro.py::_env_absent_unverifiable_reported
- src/frob/gates/_bug_repro.py::_env_absent_vars_logged
- src/frob/gates/_bug_repro.py::bug_repro_violations (wires the above)
- docs/modules/gates.md#bug002-t-1421-a-bug-ticket-must-prove-the-defect-no-longer-reproduces
- docs/modules/tickets.md#public-api
- docs/modules/tickets-landing.md (BUG002/BUG003 section)

Why: BUG002's repro subprocess inherited this verification sandbox's own
environment wholesale, so a defect whose trigger is something MISSING from
the environment (a bare CI runner's absent git identity, an unset config
var -- T-3075's own five tests) could never genuinely reproduce: the
sandbox always has the thing whose absence is the defect. Read T-3156
(landed 21055ca26f9b) first as precedent -- it faced a structurally
identical "no legitimate evidence route" gap for docs-only/Rust-only
tickets and solved it with one real-filesystem predicate
(scope_has_python_surface) wired into three existing checkpoints, not a
new evidence format or ticket field. This ticket applies the same scale
of solution: `frob:env-absent VAR1,VAR2,...` in the ticket body names
environment variables to strip from the parent-commit repro subprocess
before BUG002 runs it (HOME is redirected to a fresh empty directory
rather than deleted, since deleting it would break the subprocess
outright, not just remove the identity it carries); the repro then
genuinely observes the absence and gets a real FAILED_AT_PARENT verdict
through the SAME `_bug_repro_outcome_at_ref` classifier every other repro
already uses. No new evidence format, no new Ticket field.

For the residual this cannot mechanise (a missing binary on PATH, an
unsupported platform primitive -- no env-var strip simulates either),
`frob:env-absent-unverifiable reason="..."` reports a distinct,
ledger-visible ENV_ABSENCE_UNVERIFIABLE/UNVERIFIABLE-IN-SANDBOX outcome
instead of collapsing into an ordinary `frob:waive BUG002` -- T-1664's
doctrine that UNRESOLVED is never silently counted as either pass or
fail, applied to the one class of bug this repo's own gate is
structurally unable to verify at all.

Demonstrated on the acceptance criterion's own terms: T-3075's shape
(fallback-for-absent-var) was reconstructed with real git commits in
tests/gates/test_env_absent_bug002_repro.py, and this ticket's OWN
BUG002 evidence is designated against that test -- proven failing at the
parent commit (4b2db3aea34d611f52f3ad057ab62b1741e31dc7) through the real
`frob ticket evidence --designate-repro` tooling, not by hand:
"FAILED_AT_PARENT: ... genuinely fails at 4b2db3a... -- a real repro,
this is what BUG002 wants". Must-stay-quiet: `bug_repro_outcome_at_ref`'s
`env_absent` parameter defaults to `()`, so an ordinary code-only repro
(no `frob:env-absent` directive) is byte-for-byte unaffected --
tests/gates/test_bug_repro_at_ref_public.py's existing assertions (now
also asserting `env_absent=()`) and the full pre-existing
`tests/test_gates_mutation_evidence.py::TestBugRepro*` suite still pass
unmodified in behavior.

Waiver-count measurement (acceptance criterion): `git grep -l "frob:waive
BUG002" -- tickets/` finds 92 tickets with a BUG002 waiver. A crude
keyword scan of the two lines around each waiver
(environment|identity|sandbox|absent|missing binary|platform) matches 14
of them -- an order-of-magnitude estimate, not a strict classification
(some are false positives/negatives from prose alone), but it establishes
the class is a meaningful double-digit fraction (roughly 1 in 6-7) of
this repo's own BUG002 waiver population, not a one-off.

Scope note: bug_repro_violations already exceeded ARCH001's 60-line
threshold on main before this ticket (measured ~107-114 lines pre-
change) -- pre-existing, unwaived tech debt, not a regression this ticket
introduced. This ticket's own two new blocks were extracted into
_env_absent_unverifiable_reported/_env_absent_vars_logged (ARCH103-style
split matching this module's own precedent) rather than added inline, so
the function is now SHORTER (107 lines) than before this ticket started;
a further split to get it under 60 is a separate, larger refactor left
for a follow-up ticket rather than expanded here.

### Changed
```
 docs/modules/gates.md                       |  36 ++++
 docs/modules/tickets-landing.md             |  10 ++
 docs/modules/tickets.md                     |   9 +
 src/frob/gates/_bug_repro.py                | 261 ++++++++++++++++++++++++++--
 tests/gates/test_bug_repro_at_ref_public.py |  12 +-
 tests/gates/test_env_absent_bug002_repro.py |  97 +++++++++++
 tests/test_gates_mutation_evidence.py       |  87 +++++++++-
 tickets/T-3104/ticket.md                    |  63 ++++++-
 8 files changed, 549 insertions(+), 26 deletions(-)
```

### Evidence
- `tests/test_gates_mutation_evidence.py::TestEnvAbsent::test_single_directive_extracted` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestEnvAbsent::test_comma_separated_names_extracted_in_order` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestEnvAbsent::test_no_directive_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestEnvAbsent::test_duplicate_names_deduplicated_first_wins` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestEnvAbsentUnverifiable::test_reason_present_recognized` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestEnvAbsentUnverifiable::test_bare_directive_without_reason_not_recognized` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestEnvAbsentUnverifiableOutcome::test_unverifiable_directive_short_circuits_before_repro_run` (pytest node id, verified passing when recorded)
- `tests/gates/test_env_absent_bug002_repro.py::TestEnvAbsentBug002Repro::test_env_absent_kwarg_reproduces_identity_absence_defect_at_parent` (pytest node id, verified passing when recorded)
- `tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_wraps_the_private_classifier` (pytest node id, verified passing when recorded)
- `tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_default_base_ref_is_main` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 81 error(s), 1658 warning(s), 875 waived
- error-findings: ARCH001@src/frob/gates/_bug_repro.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3104, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SEC110@tests/test_worktree_lease_env_ambient.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, missing-argument@tests/unit/test_coordinator_scripts.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
