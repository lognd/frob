## Done report

T-3456 (LANDPARITY001/LANDPARITY002) and T-3466 (CROSSTICKET001) registered land_parity/cross_ticket_leakage in frob.gates._ALL_GATES and gave them a fixed slot in frob.gates._CANONICAL_GATE_ORDER, but neither was added to any frob.check._STAGE_GROUPS member -- the identical registered-but-unreachable omission shape as narrative_blocks (T-3030) and comment_placement (T-3249) before them, both of which document the same recurring pattern inline. Neither gate is in frob.gates._PROCESS_POOL_GATES, so both belong on the thread pool: added to gates-fast alongside their process-pool-shape siblings. test_available_stages_cover_every_gate_and_tool (the existing drift-lock regression test) now passes. Did not attempt the ticket's optional 'single home' consolidation of frob.gates._ALL_GATES and frob.check._STAGE_GROUPS into one registry -- this is the 5th occurrence of this exact desync shape (T-1044, T-1340, T-3030, T-3249, now T-3456/T-3466) and none of the prior four consolidated either, each instead relying on the same drift-lock test to keep catching it; a real single-registry refactor touches gate registration across frob.gates and frob.check broadly and is a larger, separate undertaking than this ticket's scope. No new tickets filed.

### Changed
```
 tickets/T-3486/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 16 error(s), 4060 warning(s), 866 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@changelog.d/T-2691.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3486, REL001@src/frob/__init__.py, SELFAUDIT001@tests/unit/verify/test_bisect.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
