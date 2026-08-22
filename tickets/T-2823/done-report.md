## Done report

Changed:
- src/frob/vet/_capability_c.py (frob:waive LARGE001 added)
- src/frob/vet/_capability_core.py (frob:waive LARGE001 added)
- src/frob/vet/_capability_python.py (frob:waive LARGE001 added)
- src/frob/vet/_capability_registry/_dangerous_ops_python.py (frob:waive LARGE001 added)
- src/frob/vet/_capability_registry/_matrix.py (frob:waive LARGE001 added)
- src/frob/vet/_capability_scan.py (frob:waive LARGE001 added)
- src/frob/graph/__init__.py (frob:waive LARGE001 added, alongside existing ARCH102 waiver)
- src/frob/graph/cache.py (frob:waive LARGE001 added)
- src/frob/graph/callgraph.py (frob:waive LARGE001 added, alongside existing ARCH102 waiver)
- src/frob/graph/dsl.py (frob:waive LARGE001 added)
- src/frob/graph/summary.py (frob:waive LARGE001 added)
- src/frob/arch/_patterns.py (frob:waive LARGE001 added)
- src/frob/arch/_python.py (frob:waive LARGE001 added)
- src/frob/arch/_rust.py (frob:waive LARGE001 added)

Disposition: all 14 files WAIVED, no splits performed. All 6 vet/ files are
already-documented T-1420 per-language/shared-primitive split residue
(python/c/rust/typescript/kotlin binding families plus a shared core and a
distinct aggregation/fingerprint tail T-1459's own design review already
flagged as future-follow-up scope, not today's concern). graph/__init__.py
and graph/callgraph.py already carry ARCH102 waivers whose reasoning
directly covers the LARGE001 cohesion too (one build pipeline, one
call-resolution pipeline). graph/dsl.py is one comment-DSL grammar applied
uniformly to two surfaces (source comments, markdown anchors) sharing one
verb-attribute grammar. graph/cache.py is one SQLite persistence concern
(same shape as frob.tickets._store's own LARGE001 waiver). graph/summary.py
carries an explicit T-0745 design constraint ("one engine, not two") against
splitting. arch/_python.py's walkers deliberately share one recursion
generator; arch/_rust.py deliberately mirrors _typescript.py's adapter
structure one-for-one; arch/_patterns.py is one advisory pattern-recommender
registry under one shared design-constraint header. No imports were added
or changed anywhere in this batch (comment-only edits), so the SYS003
vet -> checker flow-assertion hazard flagged for this ticket does not apply.

Evidence: tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
Filed: none (no out-of-scope work discovered; unlike T-2822's _leases.py/_setters.py,
no genuine unactioned seam was found in this batch worth a follow-up ticket)
Gates: frob check --only arch clean for LARGE001 (0 occurrences of the code
anywhere in JSON output, all 23 pre-existing arch warnings still waived);
frob check --only static shows 8 pre-existing CYCLE001 findings unrelated
to this change (comment-only edits, no import lines touched, findings span
unrelated modules like frob.lang/frob.cycle/frob.app); frob:waive BUG002
added to ticket body -- no source behavior changed, no single reproducible
defect exists to bind evidence to (judgment-call waiver ticket, same shape
as T-2375/T-2825/T-2822's own BUG002 waivers).

### Changed
```
 tickets/T-2823/ticket.md | 23 +++++++++++++++++++++--
 1 file changed, 21 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 21 error(s), 1221 warning(s), 741 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DSL001@src/frob/arch/_patterns.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2823, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
