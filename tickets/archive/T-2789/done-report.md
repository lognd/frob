## Done report

Changed:
src/frob/vet/_capability_core.py
src/frob/vet/_capability_scan.py
src/frob/vet/_closedworld.py
src/frob/vet/_capability_registry/_dangerous_ops_python.py
tests/test_vet.py
tests/test_vet_capability.py
tests/unit/test_wire001_dotted_method_call.py
tests/unit/test_wire001_fixture_parameter_access.py
tests/unit/test_wire001_property_attribute_access.py
tests/unit/test_wire001_pydantic_validator_rescue.py
tests/unit/strata/test_effects.py
tests/unit/strata/test_native_staleness.py
tests/unit/strata/test_parse.py

Evidence: 10 pytest node ids bound, covering all four touched source
files (test_vet.py covers _capability_core.py/_capability_scan.py/
_closedworld.py; test_vet_capability.py covers _capability_scan.py
further) plus each touched test file. Full-batch run: 603 collected,
0 failed.

Filed: this is child batch 7 of T-2359 (the parent reformat epic-tracking
ticket, still open pending further batches).

Gates: frob format applied ruff-check-fix (tests/test_vet.py picked up
an import-sort fix, two lines) + ruff-format-write per file; diff
reviewed by hand, format-only (whitespace/quote-style/import-order/
line-wrap), no semantic changes.

### Changed
```
 tickets/T-2789/ticket.md | 55 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 55 insertions(+)
```

### Evidence
- `tests/test_vet.py::TestLockfileParsers::test_find_lockfile_uv` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestClosedWorldAccounting::test_walk_python_imports_collects_absolute_imports_only` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_docstring_and_comment_prose_yields_no_exec_capability` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_classmethod_called_dotted_qualified_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_fixture_consumed_by_a_test_in_the_same_file_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_read_via_attribute_access_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticValidatorRescue::test_fresh_model_validator_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestNodeMayKinds::test_kinds` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_reports_native_grammar_ahead_of_native` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_parse.py::TestParseModule::test_parses_bare_module` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 19 error(s), 1317 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
