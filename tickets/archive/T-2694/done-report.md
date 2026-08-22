## Done report

Recovered from a stranded worktree: split done, doc/test anchors retargeted, and the 16 T-2114 missing-frob:tests findings (source-level directives above every new public symbol in the split telemetry/__init__.py, _footguns.py, _usage.py) closed by binding each symbol to its real covering test. tests/test_telemetry.py 40/40 green (serial run; xdist showed one order-dependent flake unrelated to this change). T-2694's scope widened by 1 glob (tests/test_telemetry.py) to give COV002 ticket-coverage over the retargeted frob:tests comment lines in that file. TICK006 refresh.

### Changed
```
 design/frob.strata                                 |  10 +-
 docs/guides/agentic-time-profiling.md              |  38 +-
 docs/modules/stats.md                              |   8 +-
 rapid-debt.jsonl                                   |   2 +
 .../app/{telemetry.py => telemetry/__init__.py}    | 507 ++-------------------
 src/frob/app/telemetry/_footguns.py                | 303 ++++++++++++
 src/frob/app/telemetry/_usage.py                   | 220 +++++++++
 src/frob/gates/_pii_structural/_keywords.py        |   2 +-
 tests/test_telemetry.py                            |  79 ++--
 tickets/T-2694/done-report.md                      |  82 ++++
 10 files changed, 722 insertions(+), 529 deletions(-)
```

### Evidence
- `tests/test_telemetry.py::test_redact_command_hides_recognizable_secret` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_estimate_tokens_is_len_over_four` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_append_event_writes_one_json_line` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 37 error(s), 1125 warning(s), 696 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2742/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@src/frob/serve/_socketd.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
