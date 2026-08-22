## Done report

Changed:
- src/frob/gates/_arch.py::_ERROR_SEVERITY_CATEGORIES (added "large-file")
- src/frob/gates/_arch.py::arch_gate (docstring updated for new severity)
- tests/test_arch_gate.py::TestArchGateLargeFile.test_large_file_fires_large001_error (renamed from test_large_file_fires_large001_warn, asserts Severity.ERROR)
- docs/modules/gates.md (LARGE001 row updated to ERROR posture)

Measurement (pre-promotion, direct against live build_graph snapshot via
frob.gates._arch.arch_gate + frob.gates._waive._apply_waivers, mirroring
the call site in src/frob/gates/__init__.py::_load_graph_queue_lock):
total LARGE001 = 88, waived = 88, unwaived = 0. Both files that blocked
the prior attempt (src/frob/tickets/_leases.py, src/frob/gates/_doclink_docanchor.py)
no longer appear in the finding set at all (leases.py carries a fresh
waiver from T-2853; doclink_docanchor.py was split under T-2843 and its
successor files are each individually waived or under threshold).

Post-promotion re-measurement (same method, after flipping severity):
total LARGE001 = 88, waived = 88, unwaived = 0, severity of all 88
findings confirmed Severity.ERROR.

tests/test_arch_gate.py and tests/unit/test_arch_srp.py: 40 passed, 0
failed (SUITE-RESULT: exitstatus=0 collected=40 failed=0).

Evidence: tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_error
bound to acceptance [0] and [1].

Filed: none -- no out-of-scope discoveries.

Gates: frob check --only static clean of directive/DSL errors for the
touched files (pre-existing frob-cycle and claude-config-drift failures
unrelated to this change, part of the currently-red main tree per
dispatch brief).

CONSEQUENCE FOR FUTURE WORK: LARGE001 is now Severity.ERROR. Any
newly-created file that crosses max_file_lines reds main immediately --
same risk class as REF001's regression to 5 tonight after its own
promotion. A future split/refactor that produces an oversized file must
land its frob:waive LARGE001 in the SAME change, not as a follow-up.

### Changed
```
 tickets/T-2831/ticket.md | 15 +++++++++++----
 1 file changed, 11 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 62 error(s), 484 warning(s), 794 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@frob-core/src/callgraph.rs, COV001@frob-core/src/exact_regions.rs, COV001@frob-core/src/lib.rs, COV001@frob-core/src/r3.rs, COV001@frob-core/src/r4.rs, COV001@frob-core/src/r5.rs, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1102, COV003@tickets/T-1651, COV003@tickets/T-1656, COV003@tickets/T-2375, COV003@tickets/T-2822, COV003@tickets/T-2823, COV003@tickets/T-2824, COV003@tickets/T-2825, COV003@tickets/T-2826, COV003@tickets/T-2829, COV003@tickets/T-2830, COV003@tickets/T-2839, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC006@docs/modules/dup-sota-survey.md, DOC006@docs/modules/dup.md, DOC006@docs/modules/graph.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/dup.md, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@docs/modules/tickets-landing.md, DRIFT002@frob-core/src/lib.rs, DRIFT002@tests/test_arch_near_duplicate_native.py, DRIFT002@tests/unit/test_dup_core.py, DSL001@tests/unit/test_coordinator_scripts.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2831/src/frob/gates/_mutation_evidence.py, F822@/home/logan/projects/frob/.claude/worktrees/t-2831/src/frob/gates/_bug_repro.py, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2831, REF001@frob-core/src/callgraph.rs, REF001@frob-core/src/exact_regions.rs, REF001@frob-core/src/r3.rs, REF001@frob-core/src/r4.rs, REF001@frob-core/src/r5.rs, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@frob-core/src/exact_regions.rs, TEST001@frob-core/src/lib.rs, TEST001@frob-core/src/r3.rs, TEST001@frob-core/src/r4.rs, TEST001@frob-core/src/r5.rs, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
