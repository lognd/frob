---
id: T-2789
title: 'Reformat batch 7/N: 13 files pending ruff-format (T-2359 child)'
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: T-2359
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_core.py
- src/frob/vet/_capability_scan.py
- src/frob/vet/_closedworld.py
- src/frob/vet/_capability_registry/_dangerous_ops_python.py
- tests/test_vet.py
- tests/test_vet_capability.py
- tests/unit/test_wire001_dotted_method_call.py
- tests/unit/test_wire001_fixture_parameter_access.py
- tests/unit/test_wire001_property_attribute_access.py
- tests/unit/test_wire001_pydantic_validator_rescue.py
- tests/unit/strata/test_effects.py
- tests/unit/strata/test_native_staleness.py
- tests/unit/strata/test_parse.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_vet.py::TestLockfileParsers::test_find_lockfile_uv
- tests/test_vet.py::TestClosedWorldAccounting::test_walk_python_imports_collects_absolute_imports_only
- tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_docstring_and_comment_prose_yields_no_exec_capability
- tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_classmethod_called_dotted_qualified_is_not_flagged
- tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_fixture_consumed_by_a_test_in_the_same_file_is_not_flagged
- tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_read_via_attribute_access_is_not_flagged
- tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticValidatorRescue::test_fresh_model_validator_is_not_flagged
- tests/unit/strata/test_effects.py::TestNodeMayKinds::test_kinds
- tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_reports_native_grammar_ahead_of_native
- tests/unit/strata/test_parse.py::TestParseModule::test_parses_bare_module
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: df28a69ece68200380f917357a27f8bf704cde0c
---
Batch 7/N of T-2359: apply ruff-format-only reformat to 13 files
(vet capability/closedworld modules, WIRE001 test files, strata
effects/native-staleness/parse tests). No semantic changes;
format-only diff.