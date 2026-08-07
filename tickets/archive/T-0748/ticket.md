---
id: T-0748
title: 'hot-graph cross-language collectors: perf (native/Rust/C/C++), V8 cpuprofile
  (TS), JFR (Kotlin) into the shared hit stream'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0710
parent: T-0709
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- src/frob/testing/**
- tests/unit/perf/
- docs/guides/extending/test-runner-entries.md
- docs/modules/perf.md
- pyproject.toml
- uv.lock
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/guides/extending/test-runner-entries.md
  reason: 'reviewer T-0748 rejection finding 2: document new RunnerSpec.collector
    field and rewrite the T-0748 perf.md section from future to delivered tense'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/modules/perf.md
  reason: 'reviewer T-0748 rejection finding 2: document new RunnerSpec.collector
    field and rewrite the T-0748 perf.md section from future to delivered tense'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: pyproject.toml
  reason: 'reviewer T-0748 rejection finding 1: REL001 requires the version bump +
    frob release stamp to be performed in this worktree (agent instructed explicitly,
    gate-affecting REL001 unwaived error)'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: 'reviewer T-0748 rejection finding 1: REL001 requires the version bump +
    frob release stamp to be performed in this worktree (agent instructed explicitly,
    gate-affecting REL001 unwaived error)'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: 'reviewer T-0748 rejection finding 1: REL001 requires the version bump +
    frob release stamp to be performed in this worktree (agent instructed explicitly,
    gate-affecting REL001 unwaived error)'
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/perf/test_collectors.py::TestParsePerfScript::test_parses_committed_fixture_into_leaf_first_stacks
- tests/unit/perf/test_collectors.py::TestParsePerfScript::test_frame_with_no_debuginfo_is_unattributed_not_dropped
- tests/unit/perf/test_collectors.py::TestParsePerfScript::test_unparseable_profile_errors_naming_the_file
- tests/unit/perf/test_collectors.py::TestParsePerfScript::test_resolves_through_shared_hotgraph_stream
- tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_parses_committed_fixture_walking_parent_chain
- tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_weight_comes_from_time_deltas
- tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_invalid_json_errors_naming_the_file
- tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_missing_required_keys_errors
- tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_resolves_through_shared_hotgraph_stream
- tests/unit/perf/test_collectors.py::TestBuildClassToFile::test_maps_unambiguous_class_to_its_file
- tests/unit/perf/test_collectors.py::TestBuildClassToFile::test_class_seen_in_two_files_is_dropped_not_guessed
- tests/unit/perf/test_collectors.py::TestParseJfrPrint::test_parses_committed_fixture_into_leaf_first_stacks
- tests/unit/perf/test_collectors.py::TestParseJfrPrint::test_unmapped_class_is_unattributed_not_dropped
- tests/unit/perf/test_collectors.py::TestParseJfrPrint::test_unparseable_profile_errors_naming_the_file
- tests/unit/perf/test_collectors.py::TestParseJfrPrint::test_resolves_through_shared_hotgraph_stream
designated_repro_test: null
acceptance:
- text: GIVEN committed fixture profiles (perf script, .cpuprofile, JFR) for equivalent
    hot-loop programs WHEN each collector ingests THEN section hits land in the shared
    store with deciles readable per language AND an unparseable profile errors naming
    the file AND unattributed weight is reported as a visible fraction
  evidence:
  - tests/unit/perf/test_collectors.py::TestParsePerfScript::test_resolves_through_shared_hotgraph_stream
  - tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_resolves_through_shared_hotgraph_stream
  - tests/unit/perf/test_collectors.py::TestParseJfrPrint::test_resolves_through_shared_hotgraph_stream
threat: null
component: null
---
User mandate 2026-07-22: the hot-graph must cover ALL supported languages, not just Python. The store/section-ids/advisories (T-0711/T-0712) are already language-neutral (symbol digests + normalized-model line spans exist for python/TS/rust/kotlin adapters; C/C++ via the existing tree-sitter parse); this ticket delivers the per-language COLLECTOR ADAPTERS converting each ecosystem native profile format into T-0710 shared (file, line, weight) hit stream: (a) NATIVE (Rust/C/C++ incl. the pyo3 strata_core/frob_core crates in-process): Linux perf record/script output (frame-pointer or dwarf stacks; mixed-mode python+native stacks attribute native frames to crate sections and python frames to the python sampler -- one profile, two resolvers); degrade gracefully (warn + empty) where perf is unavailable, per the vitest/ctest collector precedent (T-0587). (b) V8 (TS/JS): node --cpu-prof .cpuprofile JSON ingestion, hooked into the vitest runner invocation the T-0587 collector already discovers. (c) JVM (Kotlin): JFR recording ingestion (jfr print/JSON) when a JVM test runner is configured. Each adapter is a bounded parser + resolver, tested against small committed fixture profiles (never live-profiling in unit tests); frob.toml [runners] declares which collector attaches to which runner. NO-FAIL-SILENT: an unparseable profile is an ERROR naming the file; frames resolving to no known section are counted and reported as unattributed-weight (a visible number, never dropped) -- an unattributed fraction above a threshold is a finding, since it means the hot-graph is blind to real time.