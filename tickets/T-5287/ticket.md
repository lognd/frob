---
id: T-5287
title: T-5132 points-required-on-start broke ~40 pre-existing tests across 7 files
  (test fixtures never updated)
state: in-progress
kind: bug
origin: human
created: '2026-09-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_leases.py
- tests/test_ticket_work_and_land_finish.py
- tests/unit/test_app_runners_batch7.py
- tests/test_ticket_runner_archive_force.py
- tests/test_tickets_lease.py
- tests/test_tickets_no_scope.py
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/_cli_parsers/_ticket/_progress.py
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/_config_external.py
  reason: opt-in points-required gate needs the pyproject [tool.frob] loader allowlist
    entry, --require-points CLI flag, the _refuse_unsized_on_start guard itself, and
    this repo's own pyproject.toml opt-in
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: opt-in points-required gate needs the pyproject [tool.frob] loader allowlist
    entry, --require-points CLI flag, the _refuse_unsized_on_start guard itself, and
    this repo's own pyproject.toml opt-in
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: opt-in points-required gate needs the pyproject [tool.frob] loader allowlist
    entry, --require-points CLI flag, the _refuse_unsized_on_start guard itself, and
    this repo's own pyproject.toml opt-in
  actor: logan
  at: '2026-09-22'
- op: add
  glob: pyproject.toml
  reason: opt-in points-required gate needs the pyproject [tool.frob] loader allowlist
    entry, --require-points CLI flag, the _refuse_unsized_on_start guard itself, and
    this repo's own pyproject.toml opt-in
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5287
branch: t-5287
---
CI run 35717833933 on dev tip 197238c35e: a second major (after the shim
INFO-log bug) failure cluster comes from T-5132's own "points required
to start a ticket" gate (src/frob/app/ticket_runner/_lifecycle.py::
_refuse_unsized_on_start, sys.exit(1) when ticket.points is None and
ticket.unsized_ack is not set). T-5132 landed without updating the
pre-existing test suite's own ticket-creation-then-start fixtures, so
every in-process test that calls ticket_run(AppConfig(ticket_command=
"start", ...)) against a ticket created without points now exits(1)
instead of proceeding, cascading through unrelated assertions further
down each test.

Measured: 7 files call ticket_command="start" directly and fail this
way, at least (this list is not exhaustive -- it is only what a plain
grep for the literal call shape found; other tests reach _start via a
higher-level helper and may also be affected):
- tests/test_ticket_leases.py (multiple failures, e.g.
  TestCommitFullLedgerChange::test_archive_cli_leaves_repo_clean,
  TestLeaseStalenessReason, TestRefusesForeignLiveLease,
  TestReadAllLeasesReconciliation, TestReleaseOrphanedLease,
  TestStealOverride, TestDoubleDispatchIncidentRegression,
  TestLedgerAutoCommitEnumeratedOverDispatchTable)
- tests/test_ticket_work_and_land_finish.py (TestWork,
  TestLandProofAndFinish, TestBranchDriftGuard, and more)
- tests/unit/test_app_runners_batch7.py (TestTicketStart,
  TestTicketArchive, TestTicketClose, TestTicketRequeue)
- tests/test_ticket_runner_archive_force.py (TestTicketArchiveForceCLI)
- tests/test_tickets_lease.py (TestWorkCluster)
- tests/test_tickets_no_scope.py (TestRefuseEmptyScopeOnStart)
- tests/unit/test_leases_staleness_perf.py,
  tests/unit/test_lifecycle_work_base.py (indirect, via a shared
  ticket-then-start helper -- confirm exact call shape before fixing)

Fix direction (needs a decision, not guessed here): either (a) give the
shared ticket-creation test fixture/spec helper a default points value
(or unsized_ack=True) so every caller gets it for free -- check
tests/conftest.py or a shared `_spec`-style helper each of these files
already uses before touching 7 files individually, since a single
shared-helper fix would be far less risky than 7 separate edits -- or
(b) T-5132's own land should have covered this and this is really a
"T-5132 follow-up: update its own repo's test suite" ticket scoped
back to T-5132's own area. Do NOT set points on every individual
ticket_run call site by hand without first checking for a shared
helper -- that is the wrong scope if one exists.
