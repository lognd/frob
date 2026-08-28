## Done report

WIRE003 walked only frob.__main__._build_parser's argparse tree, but
frob.__main__._dispatch routes refactor/narrative by a raw argv[0] scan
BEFORE that tree is ever built, so those verbs (and refactor's real
move/rename/split/move-module subcommands) never entered the tree WIRE003
checked and were false-flagged as unresolvable. The verbs were never
broken -- the gate consulted the wrong source, exactly as the ticket
diagnosed. Did NOT touch .claude/hooks/frob-suggest.py: that hook is the
standing-directive enforcement for preferring `frob refactor`, and
weakening it would have destroyed the nudge.

Fix: _wire003_live_verb_tokens now ALSO resolves refactor/narrative's own
subcommand trees by calling their real add_refactor_parser/
add_narrative_parser registration functions against a throwaway parser
(the same technique _build_parser itself uses) -- not a second hand-typed
subcommand list, which would just relocate the staleness risk. bind/
agent/worktree/sync-skills need no such supplement: despite also being
raw-dispatched early, each still registers its own add_*_parser inside
_build_parser, so the existing walk already sees them.

AUDIT (T-3115's own ask): scope was src/frob/gates/_wire.py only, so I did
NOT touch frob.__main__.py to register refactor/narrative on the real
_build_parser tree for --help purposes -- that is a separate, in-scope-
for-a-different-ticket fix. Filed a residue ticket for it.

move-module: contrary to the ticket's own text (5 WIRE003 hits framed
`{move,rename,split}` as the full set), `frob refactor --help` today
already lists FOUR subcommands: move, rename, split, move-module.
move-module is real, registered, and documented (docs/commands/
refactor.md) -- it is not missing. The ticket's belief that it might not
exist was not borne out; no follow-up needed there.

Add-only audit was in T-3113's scope, not this ticket's -- not repeated
here.

### Changed
```
 src/frob/gates/_wire.py            | 72 +++++++++++++++++++++++++++++++++++++-
 tests/test_gates.py                | 60 +++++++++++++++++++++++++++++++
 tickets/T-3115/ticket.md           |  9 ++++-
 tickets/T-3125/ticket.md | 29 +++++++++++++++
 4 files changed, 168 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWireGate::test_wire003_direct_dispatch_verb_refactor_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire003_still_flags_a_verb_shaped_like_the_hidden_set` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire003_matcher_pattern_stale_verb_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire003_real_verbs_are_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 83 error(s), 734 warning(s), 864 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3115/ticket.md, DOC006@tickets/T-3122/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-br/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3115, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
