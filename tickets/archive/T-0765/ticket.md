---
id: T-0765
title: 'frob perf CLI: live collector wiring (perf/V8/JFR + python sampler) end-to-end
  subcommand'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
- src/frob/perf/**
- docs/modules/perf.md
- tests/system/test_cli_perf.py
- tests/unit/perf/test_collectors.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/system/test_cli_perf.py
  reason: T-0765 test evidence lives here; scope extended to cover the CLI + unit
    test files this ticket's implementation needs
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/unit/perf/test_collectors.py
  reason: T-0765 test evidence lives here; scope extended to cover the CLI + unit
    test files this ticket's implementation needs
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/perf/test_collectors.py::TestDetectCollectorFormat::test_cpuprofile_extension_is_v8
- tests/unit/perf/test_collectors.py::TestDetectCollectorFormat::test_jdk_execution_sample_marker_is_jfr
- tests/unit/perf/test_collectors.py::TestDetectCollectorFormat::test_anything_else_defaults_to_perf_script
- tests/unit/perf/test_collectors.py::TestParseCollectorFormat::test_dispatches_to_the_matching_adapter[perf-script-sample.perf.script]
- tests/unit/perf/test_collectors.py::TestBuildIndexForFiles::test_resolves_a_real_python_file_in_the_repo
- tests/unit/perf/test_collectors.py::TestBuildIndexForFiles::test_missing_or_unmapped_file_is_absent_from_the_index
- tests/unit/perf/test_collectors.py::TestLanguageDeciles::test_buckets_are_grouped_per_language_never_mixed
- tests/unit/perf/test_collectors.py::TestLanguageDeciles::test_unattributed_weight_gets_its_own_visible_bucket
- tests/unit/perf/test_collectors.py::TestLanguageDeciles::test_resolve_stream_output_feeds_language_deciles_end_to_end
- tests/system/test_cli_perf.py::TestPerfCollect::test_collect_resolves_a_real_python_hot_frame
- tests/system/test_cli_perf.py::TestPerfCollect::test_collect_json_output_is_valid_json
- tests/system/test_cli_perf.py::TestPerfCollect::test_collect_without_file_or_sampler_fails_cleanly
- tests/system/test_cli_perf.py::TestPerfCollect::test_collect_autodetects_cpuprofile_format
designated_repro_test: null
acceptance:
- text: GIVEN a repo and a recorded profile artifact (perf script output, .cpuprofile,
    or JFR print output) WHEN the user runs the frob perf collect subcommand THEN
    the hit stream is resolved through resolve_stream and per-language deciles are
    readable from the CLI output
  evidence:
  - tests/system/test_cli_perf.py::TestPerfCollect::test_collect_resolves_a_real_python_hot_frame
threat: null
component: null
---
T-0748 delivered the collector parser adapters (parse_perf_script, parse_v8_cpuprofile, parse_jfr_print + build_class_to_file) proven through resolve_stream/HitStream, but no frob perf CLI entrypoint exists for any collector including the T-0710 python sampler. Wire a subcommand that accepts a profile artifact path (or invokes the sampler), runs the matching collector, and renders the resolved hot-graph deciles. Filed per T-0748 reviewer recommendation (disclosed deviation, real unscoped work).