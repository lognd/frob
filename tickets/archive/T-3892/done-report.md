## Done report

Changed:
- src/frob/app/ticket_runner/_ledger_mirror.py::_ticket_md_path
- src/frob/app/ticket_runner/_ledger_mirror.py::_preserve_primary_only_evidence
- src/frob/app/ticket_runner/_ledger_mirror.py::_mirror_evidence_union
- src/frob/app/ticket_runner/_ledger_mirror.py::_mirror_ledger_paths
- src/frob/app/ticket_runner/_ledger_mirror.py::mirror_evidence_rebind_to_primary

Evidence:
- tests/unit/test_ticket_runner_ledger_mirror.py::TestMirrorPreservesEvidence::test_preserve_evidence_helper_unions_primary_only_ids
- tests/unit/test_ticket_runner_ledger_mirror.py::TestMirrorPreservesEvidence::test_mirror_survives_a_concurrent_coordinator_side_edit

Scope note: this is part B's independent-of-part-A "minimum fix" in spirit but
implemented as part A's actual fix -- the mirror's blind full-file overwrite
now unions evidence ids rather than letting either side (worktree or a
coordinator writing directly on primary) silently drop the other's. The
ticket's part B (loader must name conflict markers/malformed-vs-not-found)
and the broader whole-record-vs-changed-fields policy question, and the
historical blast-radius scan the ticket also asks for, are NOT done here --
out of the tight scope this series' brief declared (the mirror module and
its test file, plus one AFFECT001-required doc note). Filed T-4376 for a
SELFAUDIT001 design/frob.strata declaration gap this fix's own new fs.read
call sites surfaced (also out of scope; design/frob.strata is a repo-wide
governance file, not part of the declared scope).

Filed: T-4376 (SELFAUDIT001 fs.read declaration for _ledger_mirror.py)

Gates: frob check --ticket T-3892 -- gate:SCOPE/gate:PREWORK/diff-scoped
checks clean. Remaining repo-wide errors (COV003 on T-4346's evidence,
COV007 on _mutation_evidence.py, SELFAUDIT001 on this file's two new reads)
are either pre-existing/other-ticket noise or filed as T-4376 above, not
this ticket's own diff.
