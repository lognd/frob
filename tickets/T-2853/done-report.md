## Done report

Changed: src/frob/tickets/_leases.py (frob:waive LARGE001 directive only, no logic change)
Evidence: tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_commit_flag_warns_when_dirty (plus a 10-node lease/commit-focused subset run clean; identical 6 pre-existing failures in the full file reproduced independently on unmodified main)
Filed: none
Gates: frob check --only static shows frob-arch 23 warnings (23 waived) post-change; direct frob.gates._arch.arch_gate()/frob.gates._waive._apply_waivers() re-measurement confirms 0 unwaived LARGE001 findings for src/frob/tickets/_leases.py (was 1 unwaived pre-change). ast.parse confirms the added frob:waive directive parses cleanly (guards against the unescaped-quote comment-DSL hazard).

### Changed
```
 tickets/T-2853/ticket.md | 17 +++++++++++++++--
 1 file changed, 15 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_commit_flag_warns_when_dirty` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 45 error(s), 626 warning(s), 795 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@frob-core/src/callgraph.rs, COV001@frob-core/src/exact_regions.rs, COV001@frob-core/src/lib.rs, COV001@frob-core/src/r3.rs, COV001@frob-core/src/r4.rs, COV001@frob-core/src/r5.rs, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC006@docs/modules/dup-sota-survey.md, DOC006@docs/modules/dup.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/dup.md, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@frob-core/src/lib.rs, DRIFT002@tests/test_arch_near_duplicate_native.py, DRIFT002@tests/unit/test_dup_core.py, DSL001@tests/unit/test_coordinator_scripts.py, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, REF001@frob-core/src/callgraph.rs, REF001@frob-core/src/exact_regions.rs, REF001@frob-core/src/r3.rs, REF001@frob-core/src/r4.rs, REF001@frob-core/src/r5.rs, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@frob-core/src/exact_regions.rs, TEST001@frob-core/src/lib.rs, TEST001@frob-core/src/r3.rs, TEST001@frob-core/src/r4.rs, TEST001@frob-core/src/r5.rs, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
