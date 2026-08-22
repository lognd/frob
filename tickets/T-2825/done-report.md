## Done report

Changed:
- src/frob/tickets/_doable.py (frob:waive LARGE001 added, T-1651-grade)
- src/frob/tickets/_evidence.py (frob:waive LARGE001 added, alongside existing ARCH102 waiver)
- src/frob/tickets/_land.py (frob:waive LARGE001 added)
- src/frob/tickets/_land_finalize.py (frob:waive LARGE001 added)
- src/frob/tickets/_land_release.py (frob:waive LARGE001 added)
- src/frob/tickets/_land_squash.py (frob:waive LARGE001 added)

Disposition: all 6 files WAIVED, no splits performed. Each file's own module
docstring already documents that it is the output of one or more prior
per-family/per-stage extraction tickets (T-1103, T-1171, T-1186, T-1251,
T-1334) -- what remains in each file is one cohesive concern (dispatchable-
queue decision, DONE-transition guard chain, land lock/preflight
orchestration, draft-finalize pipeline, release-coherence transaction,
squash-apply/close transaction). For _land.py specifically, a candidate
seam (the cross-ticket-leakage/passenger-ticket preflight helpers) was
investigated and rejected: those helpers are interleaved with the
already-landed-detection helpers through shared diff-parsing primitives
(_raw_tree_for_ref, _DiffLineTracker), and every symbol in that block has
zero external callers (verified via git grep across src/frob) -- splitting
it would create a fresh import edge between two modules that immediately
import each other back, the same "no real boundary" outcome T-1651 ruled
out. No forced splits were made anywhere in this batch.

Evidence: tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
Filed: none (no out-of-scope work discovered)
Gates: frob check --only arch --ticket T-2825 clean for LARGE001 (0 findings
this code, batch files read severity=note/waived); frob:waive BUG002 added
to ticket body -- no source behavior changed, no single reproducible defect
exists to bind evidence to (judgment-call waiver ticket, same shape as
T-2375's own BUG002 waiver).

### Changed
```
 tickets/T-2825/ticket.md | 24 ++++++++++++++++++++++--
 1 file changed, 22 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 20 error(s), 1051 warning(s), 722 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2825, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
