## Done report

Changed:
- src/frob/gates/__init__.py::_anchor_mismatch_message (new)
- src/frob/gates/__init__.py::docanchor_gate (unresolved-anchor branch now delegates
  message construction to _anchor_mismatch_message)

The unresolved-anchor DOC002 message now reports the computed slug, the full set of
anchors found in the target doc file (or "(none)" if empty), and the nearest match by
edit distance via difflib.get_close_matches (cutoff=0.0, so a suggestion is always
offered when the target file has at least one anchor). Example:
"DOC002: frob:doc anchor 'docs/m.md#real-headin' does not resolve; computed slug
#real-headin does not match any anchor in docs/m.md (found: real-heading); did you
mean #real-heading?"

The other three DOC002 failure modes (missing #anchor, missing target file) are
unchanged -- this ticket only touched the "anchor exists in slug set is false" branch,
since those are the ones where guessing was blind.

Evidence: (bound via frob:tests directives, recorded with frob ticket evidence)
- tests/test_gates.py::TestDocanchorGate::test_unresolvable_anchor_reports_slug_and_nearest_match (new)
- tests/test_gates.py::TestDocanchorGate::test_unresolvable_anchor_fires
- tests/test_gates.py::TestDocanchorGate::test_missing_file_fires
- tests/test_gates.py::TestDocanchorGate::test_malformed_target_missing_fragment_fires
- tests/test_gates.py::TestDocanchorGate::test_resolvable_heading_and_explicit_anchor_pass

Filed: none (change was small and fully in scope; no out-of-scope work found)

Gates: `uv run frob check` -- gates FAIL is pre-existing baseline (40 waived-adjacent
violations unrelated to this change, e.g. PERF003 test-file waivers); ty FAIL is the
known worktree-natives artifact (strata_core/frob_core unresolved-import in nested
pytest subprocess collection, present identically on main, not a regression).
`uv run frob test --base main` selects tests/test_gates.py; the 5 Docanchor tests
above all pass. The other failures in that run (TestSysGate::test_sys001_dangling,
test_sys002_unbound, test_sys004_suppresses_sys001, test_doc003_proved_claim_passes,
test_doc003_refutes_names_obligations, TestCov002StrataModuleCoverage::
test_declaration_without_module_edge_still_fires) reproduce identically on main with
this change stashed out -- confirmed pre-existing (strata_core native-parser
unavailable in the nested pytest subprocess env), not caused by this ticket.
