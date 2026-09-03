## Done report

gate:DOCENUM (docs/modules/gates.md rule-catalog enumerate list omitted
TDD001/VERSION001/VMOD001) and one of two gate:PERF sort-in-loop findings
(src/frob/lang/_support.py) fixed. The DOC011 fix (docs/modules/tickets.md)
and the second PERF004 fix (.claude/hooks/frob-suggest.py) were dropped
from this ticket's scope after discovering live in-progress leases held
by T-3358 and T-3389 (Series EQ) on those files -- deferred to avoid a
cross-ticket collision, left unresolved for a later slice.

### Changed
```
 docs/modules/gates.md                   |  2 +-
 src/frob/app/_version_guard.py          |  1 +
 src/frob/app/check_runner.py            |  2 ++
 src/frob/app/ticket_runner/_land_cmd.py |  2 ++
 src/frob/app/ticket_runner/_verify.py   |  1 +
 src/frob/lang/_support.py               |  2 ++
 src/frob/process/_reap.py               |  3 +++
 src/frob/refactor/_verify.py            |  2 ++
 src/frob/stats/_agentic.py              |  1 +
 strata-core/src/graph/vmodel.rs         |  1 +
 strata-core/src/parse/grammar_core.rs   |  1 +
 tickets/T-3394/ticket.md      | 29 +++++++++++++++++++++++++++++
 tickets/T-3395/ticket.md      | 31 +++++++++++++++++++++++++++++++
 tickets/T-3393/ticket.md      | 15 +++++++++++++--
 tickets/T-3396/ticket.md      | 29 +++++++++++++++++++++++++++++
 tickets/T-3397/ticket.md      | 29 +++++++++++++++++++++++++++++
 16 files changed, 148 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_lang_support.py::TestPackageAudit::test_every_measured_package_is_registered` (pytest node id, verified passing when recorded)
- `tests/test_lang_support.py::TestPackageAudit::test_must_fire_unregistered_language_branching` (pytest node id, verified passing when recorded)
- `tests/test_lang_support.py::TestPackageAudit::test_must_stay_quiet_agnostic_package` (pytest node id, verified passing when recorded)
- `tests/test_lang_support.py::TestPackageAudit::test_registered_package_never_flagged_even_with_literals` (pytest node id, verified passing when recorded)
- `tests/test_lang_support.py::TestPackageAudit::test_real_repo_source_tree_is_fully_registered` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 42 error(s), 4320 warning(s), 889 waived
- error-findings: AFFECT001@src/frob/lang/_support.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC011@docs/modules/tickets.md, LARGE001@src/frob/__main__.py, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3393, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/app/check_runner.py, REL001@src/frob/app/ticket_runner/_land_cmd.py, REL001@src/frob/process/_reap.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
