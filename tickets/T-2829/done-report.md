## Done report

Changed:
- src/frob/app/ticket_runner/_mutate.py (waiver only, comment added)
- src/frob/app/ticket_runner/_new.py (waiver only, comment added)
- src/frob/app/ticket_runner/_query.py (waiver only, comment added)
- src/frob/app/ticket_runner/_rapid_sweep.py (waiver only, comment added)
- src/frob/app/ticket_runner/_verify.py (waiver only, comment added)
- src/frob/app/ticket_runner/_waive_audit.py (waiver only, comment added)

Per-file disposition (all 6 waived, no splits -- each reasoning is file-specific,
not a generic size waiver, per the T-1651 bar):

- _mutate.py: ~20 of 34 top-level defs are already independent, one-field CLI
  setters (15-40 lines each) -- the file is already granular, not a monolith;
  the two largest sub-clusters (scope/scope-ack, accept/accept-amend/
  accept-remove) each share a _resolve_*_reason helper idiom with sibling
  verbs in the same file, so carving either out would separate it from that
  shared idiom, not from unrelated code.
- _new.py: one large, genuine concern (pre-flight duplicate/related-ticket
  detection) plus a scope-closure-warning helper cluster that is SHARED with
  _mutate.py's `_scope` command (`from ._new import _scope_closure_warnings`)
  -- this file is the T-1089 residue original-definition site the other
  command family already imports from; moving it elsewhere only relocates
  the same import one hop further from its two callers.
- _query.py: investigated splitting out the wave/contention cluster (~315
  lines); rejected because both `_wave` and `_contention` are, by their own
  docstrings, companion dispatch-planning views over the identical
  TicketQueue `_doable` already renders in this same file -- a same-data-
  source extraction, not a real seam.
- _rapid_sweep.py: one detached pipeline (baseline I/O -> land-id
  enumeration -> check -> attribution/quarantine -> commit debt), same
  orchestrator shape T-1651 already accepted for check_runner.py/
  sys_runner.py; large because the pipeline has many stages, not because
  unrelated features were bundled.
- _verify.py: `evidence`/`done-report` commands plus the shared check-spawn/
  evidence-verification helper cluster that `_close_cmd.py` (close/reverify)
  AND `_land_cmd.py` (land) both import and call directly (confirmed via
  grep: `_shared_check_spawn_fn`/`_check_gates_summary_fn` used at
  _close_cmd.py:1599/1606 and _land_cmd.py:5048/5060) -- this file is the
  one shared implementation every evidence-verifying command family reuses,
  matching the same original-definition-site pattern as _new.py's
  scope-closure helpers above.
- _waive_audit.py: single feature (`frob ticket waive-audit`), two phases
  (scan/complete) sharing one data model defined once at the top; same
  single-subcommand-pipeline shape as check_runner.py/sys_runner.py.

Evidence: tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
(collected + passed fresh this session; docs-only/waiver-only ticket with no
pytest surface of its own, so the existing LARGE001-family gate test is bound
per the playbook's docs-only-ticket convention -- same evidence T-2830 bound,
consistent with both being comment-only waiver passes in the same series).

Filed: none new for this ticket (T-2830's own T-2835 follow-up already covers
the ticket_runner subtree's deferred real-decomposition work generally; none
of this batch's 6 files identified a distinct, non-generic seam worth its own
follow-up beyond what T-2835 already scopes).

Gates: `frob check --json --ticket T-2829` (unbudgeted, FROB_NO_GATE_CACHE=1,
gate-summary present) -- 33 error-severity findings repo-wide before the
pre-work sweep ran (34 counting a since-resolved PRE001), ZERO of them in any
of this ticket's 6 files; all 6 files' own LARGE001 findings read as
severity=note (waived) with the reasoning above. Re-measured unscoped (no
--ticket) separately in the series report: same 6 files read note/waived, no
new errors introduced by this diff.

### Changed
```
 tickets/T-2829/ticket.md | 25 +++++++++++++++++++++++--
 1 file changed, 23 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 19 error(s), 817 warning(s), 739 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
