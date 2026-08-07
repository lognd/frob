## Done report

Changed:
- src/frob/strata/_selfconform.py::SYS_BINDING_TOTALITY
- src/frob/strata/_selfconform.py::_binding_totality_violations
- src/frob/strata/_selfconform.py::_reachable_local_files
- src/frob/strata/_selfconform.py::_python_imports_with_lines_module
- src/frob/strata/_selfconform.py::check_self_conformance (wired SYS106 into _collect_sys_violations/_apply_sys_waivers)
- src/frob/strata/__init__.py (re-export SYS_BINDING_TOTALITY)
- docs/modules/strata.md (SYS106 section)
- tests/unit/strata/test_selfconform.py (TestBindingTotality, 3 tests)

Same landing-order note as T-0668/T-0669: this module's SYS106 code was
committed as part of T-0668's land (all three checks share one file,
built together, landed in series order) -- this ticket's own remaining
work is evidence binding + Done report.

SYS106 implements binding totality / anti-laundering: starting from every
bound node's own `.py` files, it follows resolved local python imports
(cycle-safe BFS, `frob.lang.resolve_local_import`) to build the full
reachable-file closure, then fires once per reachable `FOREIGN` file
`scan_file_capabilities` observes a capability in -- "dangerous logic
moved into a helper module not directly bound to any node but reachable
from a bound node" (T-0670's acceptance criterion, verbatim), regardless
of SYS103's own scan-prefix restriction (prefix-independent by
construction, since the reachability edge itself is the join, not a
directory prefix).

Evidence:
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires (the acceptance criterion's own scenario: a bound node imports an unbound helper that performs a network effect)
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_unreachable_foreign_file_does_not_fire_sys106
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_bound_reachable_file_does_not_fire_sys106

Filed: none new (this check has no `design/frob.strata` opt-in scope cut
-- unlike SYS104/SYS105, it always runs once any node is bound at all,
so there is no analogous "make it mandatory" follow-up; T-1113 already
covers the CHK-GATE-SYS104/105/106 registry cross-reference for all
three).

Gates: `uv run frob check --ticket T-0670` clean across prework/static/
gates-native/gates-security/test/coverage/tickets (chunked per playbook
3b). `lint` shows 5 pre-existing E501 errors in
`src/frob/vet/_supplychain.py` (outside this ticket's declared scope,
landed by a concurrent wave/ticket, confirmed unrelated to this diff --
not touched). `tickets` group's 2 gate:TICK TICK006 errors are the same
pre-existing T-1077/T-1084 phantom-draft debt noted in T-0669's Done
report, confirmed present on a bare unscoped `frob check --only tickets`
against `main` independent of this work.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestBindingTotality::test_unreachable_foreign_file_does_not_fire_sys106` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestBindingTotality::test_bound_reachable_file_does_not_fire_sys106` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 8 error(s), 1312 warning(s), 427 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:295, INV006@src/frob/gates/_todo_fmt.py, INV006@src/frob/gates/_waive_comments.py, TICK006@tickets.md
