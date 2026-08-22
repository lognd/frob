## Done report

Changed:
- src/frob/app/_config_external.py (waiver only, comment added)
- src/frob/app/ticket_runner/__init__.py (waiver only, comment added)
- src/frob/app/ticket_runner/_close_cmd.py (waiver only, comment added)
- src/frob/app/ticket_runner/_land_cmd.py (waiver only, comment added)
- src/frob/app/ticket_runner/_lifecycle.py (waiver only, comment added)

Per-file disposition (all 5 waived, no splits -- each reasoning is file-specific,
not a generic size waiver, per the T-1651 bar):

- _config_external.py: ~510 of 835 lines are data (6 field-name tuples the
  module's own docstring already explains); the rest is one _apply_*_fields
  helper per tuple. No consumer-set seam -- splitting would separate a
  field-type's tuple from the one loop that reads it.
- ticket_runner/__init__.py: single CLI dispatch/wiring hub. Its own docstring
  documents that re-exported names (_root_release_manifest, _covers_scope_for_
  ticket, etc.) are re-exported HERE specifically so tests' `monkeypatch.
  setattr(ticket_runner, ...)` and cross-family callers reaching back via
  `from frob.app import ticket_runner as _ticket_runner` observe the patch --
  moving names elsewhere breaks that observably, not cosmetically.
- _close_cmd.py: investigated a real-looking seam (obligation predicates vs.
  command entrypoints) and rejected it -- _land_cmd.py reuses these exact
  predicates (_covers_scope_for_ticket, _close_gate_claims_for_ticket) rather
  than duplicating them, so they are shared close/land logic, not a distinct
  _close_cmd-only concern. Filed T-2835 to design a real extraction.
- _land_cmd.py: single `land`/`merge-driver` command family (114 helpers, all
  reachable only from _land/_merge_driver per its own docstring) -- same shape
  T-1651 already accepted for check_runner.py/sys_runner.py, just larger
  because land has more phases. This dispatch's own brief named this file as
  the highest-risk one to touch (every agent's own land depends on it);
  conservative call per that brief. Filed T-2835 to scope a real
  phase-boundary split as its own reviewed ticket.
- _lifecycle.py: investigated the worktree-provisioning cluster (_work,
  _work_cluster, _start_cluster_members, etc.) as a candidate seam; rejected
  because those functions call _start directly (the state-transition
  entrypoint) to finish what they set up -- a module split puts _start on one
  side and its own callers on the other, a circular import, not a real seam,
  without also restructuring _start's coupling (bigger than this ticket).
  Filed T-2835 to evaluate that restructuring.

Evidence: tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
(collected + passed fresh this session; docs-only/waiver-only ticket with no
pytest surface of its own, so the existing LARGE001-family gate test is bound
per the playbook's docs-only-ticket convention).

Filed: T-2835 (renumbers at land) -- "Evaluate real decomposition
seams for _close_cmd/_land_cmd/_lifecycle (ticket_runner)", scoped to design
the extraction/restructuring these three files' waivers each identified as
blocking a real split, rather than doing it under a batch LARGE001 pass.

Gates: `frob check --json --ticket T-2830` (unbudgeted, FROB_NO_GATE_CACHE=1,
gate-summary present) -- 32 error-severity findings repo-wide, ZERO of them
in any of this ticket's 5 files; all 5 files' own LARGE001 findings read as
severity=note (waived) with the reasoning above. Re-measured unscoped (no
--ticket) separately: same 5 files read note/waived, no new errors introduced
by this diff (see series report for the full unscoped diagnostic list).

Note: src/frob/app/_check_chunking.py was removed from T-2830's original
scope (T-2369 held an active lease on it at start time) -- not disposed of in
this ticket. It remains an open LARGE001 finding; T-2830's own body's file
list should be treated as this one caveat short of complete, and whoever
next has a clear lease on it should pick it up (T-2369 itself, or a fresh
child ticket once T-2369 clears).

### Changed
```
 tickets/T-2830/ticket.md           | 25 ++++++++++++++++++++++++-
 tickets/T-2835/ticket.md | 31 +++++++++++++++++++++++++++++++
 2 files changed, 55 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 19 error(s), 810 warning(s), 721 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md

### Acceptance amendments
- [1] remove: removed "given the 5 in-scope files, when frob check --json runs unbudgeted, then each file's LARGE001 finding reads as severity=note (waived) with T-1651-grade per-file reasoning naming the specific reason no split seam exists, not a generic size waiver" (reason: duplicate criterion from a retried command (the first attempt's exit-143 report was misleading -- it had already written); logan, 2026-08-21)
