## Done report

Changed:
- src/frob/gates/_mutation_evidence.py (removed 15 dead imports left behind by T-2851's split; added a documenting noqa comment to the 5 genuinely-used re-export imports from _bug_repro.py)
- src/frob/gates/_bug_repro.py (removed `mutation_evidence_violations` from __all__ -- it was never defined in this file, only in _mutation_evidence.py)
- docs/guides/agent-playbook.md (new section 4c: split-hygiene checklist -- REF001/DRIFT002/COV001/TEST001/F401/F822 -- citing T-2846/T-2695/T-2851 as the three same-night instances, per coordinator directive to record the lesson at point of use rather than only in a Done report)

Evidence:
- tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_reason_present_suppresses
- Full targeted re-run: tests/test_gates_mutation_evidence.py + tests/gates/test_mutation_evidence_err_branches.py (64/64 passed), tests/test_tickets_mutation_evidence.py -k "mutation_evidence or bug_repro" (18/18 passed)
- frob check --only lint: ruff-check 0 findings on both files (was 21: 20x F401 + 1x F822)

Filed: none new (this ticket itself was filed as T-2864 while verifying T-2855's land; no further out-of-scope discoveries this pass)

Gates: frob check --only lint clean on both scoped files post-fix. Did not run the full unbudgeted repo-wide frob check a second time for this narrow fix (already re-measured main after T-2855; this ticket's own before/after is the ruff-check diagnostic count on the two scoped files, 21 -> 0).

Verification method for each F401 before deleting (per the coordinator's explicit caution): grepped each name for non-import-line occurrences in the file, and git-grepped the repo for any importer of that name FROM this module (none found) before removing -- none were re-exports, all were genuinely dead code left behind when the code that used them moved to _bug_repro.py.

### Changed
```
 tickets/T-2864/ticket.md | 52 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 52 insertions(+)
```

### Evidence
- `tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_reason_present_suppresses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 37 error(s), 528 warning(s), 794 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1102, COV003@tickets/T-1651, COV003@tickets/T-1656, COV003@tickets/T-2375, COV003@tickets/T-2822, COV003@tickets/T-2823, COV003@tickets/T-2824, COV003@tickets/T-2825, COV003@tickets/T-2826, COV003@tickets/T-2829, COV003@tickets/T-2830, COV003@tickets/T-2839, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC006@docs/modules/graph.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@docs/modules/tickets-landing.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2864, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
