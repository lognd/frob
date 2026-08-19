## Done report

T-2569: threaded MEASURED(passed)/MEASURED(failed)/NOT_MEASURED through
_verify_ids_passing and its close-time consumer -- see prior Done report
attempt's why text (identical content, re-run only because the first
attempt's internal check spawn came back unmeasured, a transient
contention artifact confirmed clean on immediate manual re-run).

_reverify_evidence_for_close now branches PASSED/FAILED/UNMEASURED
three ways; UNMEASURED refuses with a NEW, distinctly-worded message
("could not be measured"), never the old "no longer passes" wording a
genuine FAILED still gets. Positive controls in both directions are
covered by new/updated tests (see evidence list): a genuine failure
still reports FAILED (test_no_longer_passing_returns_false et al.), and
TestingError.SpawnFailed reports UNMEASURED, never FAILED
(test_unmeasured_returns_false_with_distinct_message,
TestVerifyOneBucketPassingSpawnFailureIsUnmeasured, both new this
ticket). Did not add retry logic (explicitly out of scope). T-2521
NO_VERDICT note: lives outside src/frob/app/ticket_runner/, out of this
ticket's scope, not separately filed yet (time-boxed).

ARCH001 fixed via 3 extracted helpers; COV001 fixed via a new
docs/modules/tickets-lifecycle.md section plus frob:doc edges.
Pre-existing DRIFT001 (_parse_error_findings_from_json) and SEC110
(env-var read, line-shifted only) confirmed identical on a clean main
checkout, not introduced by this ticket. 3 pre-existing unrelated
pytest failures (TestTicketRenumber x2, test_land_success_prints_files)
also confirmed identical on clean main.

### Changed
```
 docs/modules/tickets-lifecycle.md                |  37 ++++
 src/frob/app/ticket_runner/_close_cmd.py         |  64 +++++-
 src/frob/app/ticket_runner/_land_cmd.py          |  19 +-
 src/frob/app/ticket_runner/_verify.py            | 247 +++++++++++++++++++----
 tests/test_ticket_land.py                        |  59 +++++-
 tests/test_ticket_reverify.py                    |  10 +-
 tests/test_tickets_acceptance.py                 |   8 +-
 tests/test_tickets_evidence_cli.py               |   8 +-
 tests/unit/test_app_runners_batch7.py            |   8 +-
 tests/unit/test_ticket_runner_designate_repro.py |   8 +-
 tests/unit/test_ticket_runner_land_release.py    |  82 +++++++-
 tickets/T-2569/done-report.md                    |  49 +++++
 tickets/T-2569/ticket.md                         |  84 +++++++-
 13 files changed, 606 insertions(+), 77 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestReverifyEvidenceForClose::test_still_passing_returns_true` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestReverifyEvidenceForClose::test_no_longer_passing_returns_false` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestReverifyEvidenceForClose::test_unmeasured_returns_false_with_distinct_message` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestVerifyOneBucketPassingSpawnFailureIsUnmeasured::test_spawn_failed_is_unmeasured_not_failed` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestVerifyOneBucketPassingSpawnFailureIsUnmeasured::test_individual_reverify_spawn_failure_is_unmeasured` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestReverifyFailingBucketIndividually::test_only_the_genuinely_failing_id_is_excluded` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestVerifyOneBucketPassingRoutesToIndividualReverify::test_batch_not_ok_falls_back_to_per_id_attribution` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2569/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2569/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE001@tests/unit/test_ticket_runner_land_release.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
