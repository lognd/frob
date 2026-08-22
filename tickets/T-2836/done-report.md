## Done report

Batch 3/N of T-2369's REG008 burn-down: the final entry left by T-2812
(batch 1, 36->18) and T-2832 (batch 2, 18->1, excluding CHK-GATE-DOC012
which was blocked by T-2359's live lease on src/frob/gates/_docblocks.py).
The coordinator released T-2359's leaked lease, unblocking this file.

Added the missing `# frob:enforces CHK-GATE-DOC012` directive directly
above `doc012_gate` in src/frob/gates/_docblocks.py.

A fresh full unbudgeted `frob check --json` after this fix shows REG008
dropped from 1 to... 3, not 0: three entries this ticket had NOT yet
accounted for (CHK-GATE-SYS108, CHK-GATE-SYS110,
SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE) all site in
src/frob/strata/_selfconform.py, whose directives were drafted then
reverted in T-2832's batch after a land-time CrossTicketLeakage refusal
(T-2729, queued, declares that file in its own scope to split it by
SYS1xx rule family). REG008 severity stays WARN in this batch; true zero
still requires T-2729 to land or release that scope.

frob:no-behavior-change reason="adds one frob:enforces comment directive above the existing doc012_gate function; runtime behavior, return values, and existing tests are unchanged -- this is metadata linking code to a registry entry, not logic"

### Changed
```
 tickets/T-2369/ticket.md | 44 ++++++++++++++++++++++++++++
 tickets/T-2836/ticket.md | 76 ++++++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 120 insertions(+)
```

### Evidence
- `tests/test_gates.py::TestDoc012CommandSectionGate::test_documented_subcommand_passes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 20 error(s), 926 warning(s), 728 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2836, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
