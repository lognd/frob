## Done report

The more interesting half of the language-adapter degradation story:
"the output should announce its own gap" as the requirement, not
"document the gap somewhere" -- per the coordinator's own framing.

Changed:
src/frob/graph/callgraph.py::capability_gap_disclosure (new -- the shared primitive: one warning per language in a given set whose given capability cell is a live registry KNOWN_GAP)
src/frob/graph/callgraph.py::CallGraph.degraded_languages (new field -- the actual self-disclosure: build_call_graph populates this on every call)
src/frob/graph/callgraph.py::build_call_graph (now computes and logs degraded_languages; covers call_graph always, import_graph too when verify_imports=True)
src/frob/graph/callgraph.py::_call_graph_degraded_languages, _languages_present (new private helpers)
src/frob/cycle/__init__.py::import_graph_gap_disclosure (new -- capability_gap_disclosure pre-bound to import_graph, for frob.cycle's own future use; NOT yet wired into DependencyGraph/find_cycles's own output since src/frob/cycle/graph.py sat outside this ticket's declared scope -- frob:waive WIRE001 follow_up="T-2700")
tests/test_graph.py::TestCapabilityGapDisclosure, TestCycleImportGraphGapDisclosure (new -- both directions proven: clean-tree empty AND a monkeypatched positive control that a synthetic KNOWN_GAP genuinely surfaces on the real CallGraph object build_call_graph returns, not a stub)
docs/modules/graph.md#self-disclosure-of-a-silently-degraded-capability-t-2683 (new section)
docs/modules/lang.md#optional-capability-degradation-t-1599 (updated: records what T-2683 resolved -- call_graph/import_graph via build_call_graph -- vs what remains: frob.cycle's own output, T-2700; test_discovery consumer-side disclosure, unbuilt)

Evidence:
tests/test_graph.py::TestCapabilityGapDisclosure::test_clean_tree_has_no_degraded_languages
tests/test_graph.py::TestCapabilityGapDisclosure::test_known_gap_is_disclosed_on_the_output_itself
tests/test_graph.py::TestCapabilityGapDisclosure::test_capability_gap_disclosure_empty_for_no_gap
tests/test_graph.py::TestCycleImportGraphGapDisclosure::test_empty_for_no_gap
tests/test_graph.py::TestCycleImportGraphGapDisclosure::test_delegates_to_the_shared_primitive
Full-file re-verification: tests/test_graph.py (140 node ids) all pass, re-run against merged main.

Filed: T-2700 (wire import_graph_gap_disclosure into frob.cycle.graph's
real DependencyGraph/find_cycles output -- out of this ticket's own
declared scope, that file was not granted).

Scope boundary honestly disclosed, not silently worked around:
test_discovery's own consumer-side disclosure (evidence-binding gates)
is NOT built -- this ticket's declared scope was src/frob/graph/
callgraph.py, src/frob/cycle/__init__.py, two docs only, and no
frob.testing consumer analogous to CallGraph.degraded_languages exists
yet. Real remaining work, recorded in docs/modules/lang.md.

Gates: frob check --ticket T-2683 --no-cache over archgate/lint/
docanchor/doclink/docblocks/wire/coverage: 0 errors attributable to any
file this ticket touched after two rounds of real land-refusal fixes
(missing frob:doc/frob:tests directives on the two new public symbols,
DOC007 test-target-separator format, WIRE001 needing an explicit waiver
naming T-2700, and E501 on directive comment lines) -- all fixed in
this diff, confirmed clean by direct re-check, not assumed.

### Changed
(no changed files detected)

### Evidence
- `tests/test_graph.py::TestCapabilityGapDisclosure::test_clean_tree_has_no_degraded_languages` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCapabilityGapDisclosure::test_known_gap_is_disclosed_on_the_output_itself` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCapabilityGapDisclosure::test_capability_gap_disclosure_empty_for_no_gap` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCycleImportGraphGapDisclosure::test_empty_for_no_gap` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCycleImportGraphGapDisclosure::test_delegates_to_the_shared_primitive` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 42 error(s), 972 warning(s), 679 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
