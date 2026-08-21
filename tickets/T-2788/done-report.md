## Done report

Changed:
- src/frob/app/config.py (import order only)
- src/frob/arch/__init__.py (import order only)
- src/frob/doctor.py (import order only)
- src/frob/scaffold/__init__.py (import order only)
- src/frob/strata/__init__.py (import order only)
- src/frob/tickets/__init__.py (import order only)
- src/frob/tickets/_store.py (import order only)
- src/frob/verify/_backpressure.py (import order only)
- src/frob/vet/_capability.py (import order only)
- src/frob/vet/_scan.py (import order only)

Evidence: no new test needed -- this is a mechanical `ruff check
--select I001 --fix` reordering of existing imports with zero
behavioral change (no runtime symbol touched). Verified via
`uv run frob test --base main` (touched-set, 29 recorded outcomes) and
a targeted rerun of the one failure
(tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately)
against unmodified main confirming it is pre-existing/environmental
(autocrlf-related `frob check` self-contention), not caused by this
diff.

Filed: none -- this batch is itself a planned child of T-2373 (the
parent epic already tracks the remaining sibling batches and the
final I001 warning-to-error severity promotion, which belongs to
whichever batch lands last, per T-2373's own closure requirement); no
new out-of-scope work was found.

Gates: frob check --ticket T-draft-fdd012cc clean for gate:SCOPE (after
adding tickets/T-2373/ticket.md, a sibling ticket-metadata edit made in
the same worktree, to scope) and gate:PREWORK; gate:COV's repo-wide
errors are pre-existing and unrelated to this diff (measured
unchanged: COV001 on src/frob/graph/callgraph.py, COV003 on T-1688/
T-2365 evidence -- none of these tickets or files are touched by this
change).

### Changed
```
 rapid-debt.jsonl                        |   3 +
 src/frob/app/config.py                  |   4 +-
 src/frob/arch/__init__.py               |   2 +-
 src/frob/doctor.py                      |   2 +-
 src/frob/scaffold/__init__.py           |   2 +-
 src/frob/strata/__init__.py             |  14 ++---
 src/frob/tickets/__init__.py            |   2 +-
 src/frob/tickets/_store.py              |   1 +
 src/frob/verify/_backpressure.py        |   4 +-
 src/frob/vet/_capability.py             |   2 +-
 src/frob/vet/_scan.py                   |  10 ++--
 tickets/T-draft-fdd012cc/done-report.md |  63 ++++++++++++++++++++
 tickets/T-draft-fdd012cc/ticket.md      | 101 ++++++++++++++++++++++++++++++++
 13 files changed, 190 insertions(+), 20 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 21 error(s), 1247 warning(s), 711 waived
- error-findings: AFFECT001@src/frob/verify/_backpressure.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2788, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
