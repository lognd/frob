## Done report

T-2681 (landed 2026-08-19, before T-3113 was authored) already added
`frob ticket unblock <id> --by <blocker>` with refuse-loudly-on-missing-
edge semantics -- the ticket's premise that no inverse verb existed at
all was stale (coordinator-confirmed: T-3113 was filed on that false
premise). The real, narrower gap: --reason was optional and never
recorded, so a correction to blocked_by (a load-bearing field driving
doable, the dispatch closure, epic rollups, and T-3087's close guard)
left no audit trail, unlike every other correction verb in this family
(drop/reopen/set-parent/accept --remove all require --reason).

Made --reason mandatory on unblock and record it as a dated line under a
new '## Unblock log' ticket-body section, mirroring frob ticket reopen's
(T-3087) explicit-audited-escape-hatch shape exactly. A ticket whose last
blocker was removed now carries that section; a ticket that never had a
blocker does not -- satisfying the acceptance criterion that the two
cases be distinguishable in the record without a new ledger field.

Split _unblock into _validate_unblock_args + _build_unblocked_ticket +
_unblock (ARCH001, function-length threshold) and added `assert`
narrowing casts where the split broke ty's cross-function None-narrowing
of cfg.ticket_id/ticket_by/ticket_reason. Updated docs/modules/
tickets-lifecycle.md (AFFECT001 doc-drift) with a T-3113 paragraph next
to the existing T-2681 unblock paragraph.

INVARIANTS CHECKED: T-3087's close guard and `frob ticket doable` both
read `ticket.blocked_by` live off the ledger at call time -- `_unblock`
writes that tuple through the same `write_ticket` path `_block` already
uses, so both observe the removal immediately, no caching layer in
between (confirmed by reading _build_unblocked_ticket/write_ticket and
by test_unblock_removes_edge/test_block_then_unblock_round_trips
re-loading via load_queue post-write).

ADD-ONLY AUDIT (T-3113's own ask, corrected per coordinator note):
reviewed the full `frob ticket --help` verb surface. Original framing
("one add-only verb found") was wrong along with the ticket's own
premise -- `unblock` already existed and already refused loudly on a
missing edge; the real finding is ONE genuine gap, ALREADY CLOSED AT THE
EDGE LEVEL, with only a recording gap (no mandatory --reason) left,
which this ticket now closes. `label` (--add/--remove) and `accept`
(append/amend/--remove) already have real inverses -- not gaps.
`set-parent`/`priority`/`kind`/`tier`/`milestone`/`sprint`/`component`/
`runs-last` are single-value SETTERS, not accumulators -- already
correctable by calling again with a different value, a different defect
shape than blocked_by's list-append. Whether any of those can be cleared
back to null/unset is a separate, lower-severity question this pass did
not chase further; flagging it here rather than filing a ticket for an
unconfirmed gap.

NOTE ON TOOLING: verified `move-module` exists using `uv run frob
refactor --help` (shows {move,rename,split,move-module}) -- the
coordinator separately found the bare `frob` on PATH is a stale global
install with a different CLI surface (missing move-module, missing
unblock entirely) reporting the same version string. `uv run frob` used
throughout this ticket's own verification.

### Changed
```
 docs/modules/tickets-lifecycle.md          |  15 +++
 src/frob/_cli_parsers/_ticket/_closeout.py |  15 ++-
 src/frob/app/ticket_runner/_lifecycle.py   | 157 +++++++++++++++++++++--------
 tests/test_ticket_lifecycle.py             |  76 +++++++++++++-
 tickets/T-3113/ticket.md                   |  39 ++++++-
 5 files changed, 256 insertions(+), 46 deletions(-)
```

### Evidence
- `tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_removes_edge` (pytest node id, verified passing when recorded)
- `tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_refuses_when_not_present` (pytest node id, verified passing when recorded)
- `tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_refuses_invalid_ref` (pytest node id, verified passing when recorded)
- `tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_requires_reason` (pytest node id, verified passing when recorded)
- `tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_records_reason_in_unblock_log` (pytest node id, verified passing when recorded)
- `tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_leaves_other_blockers_intact` (pytest node id, verified passing when recorded)
- `tests/test_ticket_lifecycle.py::TestBlockThenUnblockRoundTrip::test_block_then_unblock_round_trips` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 81 error(s), 761 warning(s), 864 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3122/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-br/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
