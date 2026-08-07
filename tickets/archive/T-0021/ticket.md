---
id: T-0021
title: 'frob.perf: profiling, heat-maps, PERF linear-scan rules (docs/modules/perf.md)'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- src/frob/policy/**
- src/frob/app/**
- src/frob/gates/__init__.py
- src/frob/__main__.py
- docs/modules/perf.md
- docs/index.md
- tests/test_perf.py
- tests/system/test_cli_perf.py
- tickets/T-0021-frob-perf-profiling-heat-maps-perf-linear-scan-rules-docs-perf-md.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_perf.py::test_perf001_fires_on_list_membership_in_loop
- tests/test_perf.py::test_perf001_does_not_fire_on_set_membership_in_loop
- tests/test_perf.py::test_perf001_does_not_fire_outside_a_loop
- tests/test_perf.py::test_perf002_fires_on_index_call_in_loop
- tests/test_perf.py::test_perf002_does_not_fire_outside_a_loop
- tests/test_perf.py::test_perf003_fires_on_nested_loop_equality_join
- tests/test_perf.py::test_perf003_does_not_fire_on_single_loop
- tests/test_perf.py::test_perf004_fires_on_sort_in_loop
- tests/test_perf.py::test_perf004_does_not_fire_on_sort_outside_a_loop
- tests/test_perf.py::test_profile_command_and_load_artifact_round_trip
- tests/test_perf.py::test_load_artifact_no_artifact_is_err
- tests/test_perf.py::test_heat_joins_pstats_rows_onto_symbol_spans
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_profile_then_heat_shows_hot_function
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_heat_json_output_is_valid_json
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_heat_without_artifact_fails_cleanly
- tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero
designated_repro_test: null
threat: null
component: null
---
