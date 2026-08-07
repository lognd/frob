## Done report

Changed:
- src/frob/app/graph_runner.py: new `_run_affects` (`frob graph affects <ref>`), `_affects_json_payload`/`_render_affects_lines` helpers, dispatch case in `run()`.
- src/frob/app/config.py: `graph_max_depth`/`graph_max_nodes` (`int | None`) AppConfig fields, wired into the existing int-field collection loop.
- src/frob/__main__.py: `graph affects` subparser (`--json`/`--max-depth`/`--max-nodes`) registered under `_add_graph_parser`.
- src/frob/gates/__init__.py: new `affect_drift_gate` (AFFECT001 stale doc / AFFECT002 stale dependent code), `_affect_ref_file`/`_affect001_violation`/`_affect002_violation` helpers; registered gate name `affect_drift` in `_ALL_GATES`/`_CANONICAL_GATE_ORDER`/`_build_jobs`; rule ids added to `_KNOWN_GATE_RULES`; `affect_drift_gate` exported via `__all__`.
- src/frob/check/__init__.py: `affect_drift` added to the `gates-fast` `_STAGE_GROUPS` entry (required by `TestCheckStageGroups.test_available_stages_cover_every_gate_and_tool`).
- README.md: `frob graph` command-table row description updated to mention `affects`.
- docs/modules/graph.md: `#affects` section rewritten to document the new CLI subcommand and the `affect_drift_gate` enforcement half, replacing the "deliberately NOT built"/"future work" prose T-0325 left.
- docs/modules/app.md: `graph_runner.run` bullet updated (affects dispatch + new AppConfig fields); a short note added to the Config section for the two new fields.
- docs/modules/gates.md: two new rule-catalog rows (AFFECT001/AFFECT002) plus a full "AFFECT001 AFFECT002 (T-0628)" detail section; `affect_drift_gate` added to the Public API `frob:describes` list.
- tests/test_graph_affects_runner.py (new): `TestGraphAffectsRunner` -- requires-ref, unresolvable-ref, human mode, JSON mode, truncated-closure cases for `_run_affects`.
- tests/test_gates_affect_drift.py (new): `TestAffectDriftGate` -- silent-on-empty-closure, stale-doc, stale-dependent-code, and clean-when-touched cases for `affect_drift_gate`.

Evidence:
- tests/test_graph_affects_runner.py::TestGraphAffectsRunner::test_affects_requires_ref
- tests/test_graph_affects_runner.py::TestGraphAffectsRunner::test_affects_unresolvable_ref_exits_1
- tests/test_graph_affects_runner.py::TestGraphAffectsRunner::test_human_mode_reports_dependents_docs_tests
- tests/test_graph_affects_runner.py::TestGraphAffectsRunner::test_json_mode_payload
- tests/test_graph_affects_runner.py::TestGraphAffectsRunner::test_truncated_closure_flagged
- tests/test_gates_affect_drift.py::TestAffectDriftGate::test_no_closure_is_silent
- tests/test_gates_affect_drift.py::TestAffectDriftGate::test_stale_dependent_doc_flagged
- tests/test_gates_affect_drift.py::TestAffectDriftGate::test_stale_dependent_code_flagged
- tests/test_gates_affect_drift.py::TestAffectDriftGate::test_clean_when_closure_also_touched
- tests/system/test_cli_check.py -k StageGroups (4 passed) -- confirms `affect_drift`'s new stage-group membership keeps `_ALL_GATES`/`_STAGE_GROUPS` in sync.

Filed: none (REG010 fired WARN-only for AFFECT001/AFFECT002 missing a check-coverage.yaml entry; docs/design/registry/** is outside this ticket's declared scope and REG010 is advisory, not blocking -- left as-is rather than widening scope again for a warn-tier registry hygiene row).

Gates: `frob check . --only gates-fast --ticket T-0628` clean (0 errors, after a `frob ticket sweep T-0628` pre-work-sweep fix and two `AFFECT001` self-catches on this diff's own `docs/modules/app.md` obligations, resolved by documenting the new fields/dispatch there rather than waiving). `frob check . --only gates-native --ticket T-0628` clean. `frob check . --only gates-security --ticket T-0628` clean. `frob check . --only lint --ticket T-0628` clean (0 errors, 0 warnings after ruff-format/E501 fixes). `frob check . --only static --ticket T-0628` clean (pre-existing exports/arch findings only, unrelated to this change). `frob test --base main` (touched-set): python suite exit=0, PASS.
