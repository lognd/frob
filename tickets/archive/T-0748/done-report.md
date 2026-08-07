## Done report

Added three T-0748 collector adapters in src/frob/perf/_collectors.py,
all producing frob.perf._hotgraph.SampledStack/SampledFrame so T-0710's
resolve_stream needs zero changes:

- parse_perf_script: Linux perf script textual output (native/Rust/C/C++
  incl. pyo3 strata_core/frob_core in-process). Frames with a (file:line)
  debuginfo suffix resolve; frames without it (or a whole unparseable
  profile) never silently vanish -- a totally-unparseable profile is
  Err(BadPerfScript) naming the source file, a frame missing debuginfo
  gets file="" line=0 (honestly unattributed, matching _hotgraph's
  DEGRADE-TO-CORRECT discipline).
- parse_v8_cpuprofile: node --cpu-prof V8 .cpuprofile JSON (TS/JS),
  rebuilding the parent chain from the node/children tree since V8 only
  stores child pointers; lineNumber's 0-based convention converts to
  this repo's 1-based SampledFrame.line. Invalid JSON or a missing
  nodes/samples key is Err(BadCpuProfile) naming the source file.
- parse_jfr_print / build_class_to_file: jfr print --events
  jdk.ExecutionSample text output (Kotlin/JVM). JFR's own frame shape
  carries only (class.method, line), never a file path, so
  build_class_to_file derives a class->file map from the same
  NormalizedModules build_section_index indexes; a class name seen in
  more than one file is dropped from the map (ambiguous, never guessed)
  rather than risking a silently-wrong file attribution. An unmapped
  class's frame still parses with file="", contributing to visible
  HitStream.unattributed_weight instead of being dropped.

Also extended RunnerSpec (src/frob/testing/_models.py) with a
collector: str = "" field and _parse_runner_entry
(src/frob/testing/_runners.py) to read/validate a [[test.runner]]
entry's collector (one of "", "perf", "v8", "jfr") against a fixed
allowlist -- this is the frob.toml [runners] declaration the ticket's
plan item (c) calls for, wiring which collector attaches to which
runner without touching run_selected's execution path (out of scope
for this pass; the field is declared and validated, not yet consumed
by a live-invocation hook).

Deviation: the ticket's acceptance criterion names "committed fixture
profiles for equivalent hot-loop programs" across all three formats
with "deciles readable per language" -- this pass delivers the parser
adapters plus committed fixtures and proves each one resolves through
the existing T-0710 resolve_stream/HitStream (unattributed_weight
included), which is the full collector contract T-0710 defined. It does
NOT wire a live frob perf CLI subcommand that shells out to real
perf/node/jfr binaries and computes cross-language deciles end-to-end --
that would require live-profiling infrastructure the ticket explicitly
says unit tests must NOT depend on, and no such CLI entrypoint exists
yet for any collector (including the T-0710 python sampler). Not filed
by this worktree -- the coordinator disclosed that the follow-up
CLI-wiring ticket was opened directly on main as T-0765; T-0765 may not
yet be visible in this worktree's own ledger snapshot (a visibility gap,
not a phantom filing claim).

### Rework (round 2, reviewer rejection)

Three findings fixed:

1. REL001 (gate:REL): the new public API surface (parse_perf_script,
   parse_v8_cpuprofile, parse_jfr_print, build_class_to_file,
   CollectorError, RunnerSpec.collector) is a minor bump per diff_class.
   Bumped pyproject.toml version 0.96.0 -> 0.97.0 and ran
   `uv run frob release stamp`. `uv run frob check --only release
   --ticket T-0748` now passes clean (gate:REL 0 errors).
2. Documentation content gap: docs/guides/extending/test-runner-entries.md
   now documents the collector field's valid values ("", "perf", "v8",
   "jfr") and what each means. docs/modules/perf.md gained a new
   "Cross-language collector adapters (T-0748)" section (replacing the
   old future-tense forward-reference) documenting the module location,
   the four public functions, the CollectorError contract
   (BadPerfScript/BadCpuProfile/BadJfrPrint) and the
   unattributed-not-dropped frame policy. Both files were added to
   T-0748's scope via `frob ticket scope --add` with a reason before
   editing. No DRIFT/ack obligation fired for either file after editing
   (`frob check --only drift/docanchor/doclink/docblocks/refs
   --ticket T-0748` all clean), so no `frob ack` call was needed.
3. This Done report's Evidence section previously read "(no evidence
   recorded)" despite the ticket's evidence: array already listing 15
   node ids -- a prose bug, not a missing-evidence bug. Regenerated via
   `frob ticket done-report` so Evidence auto-fills from the ticket's
   real evidence array.

### Rework (round 3, acceptance criterion [0] UNBOUND)

Re-review found acceptance criterion [0] itself unbound. Its four
clauses and how each is actually discharged:

(a) "section hits land in the shared store" -- proven by the three
    `test_resolves_through_shared_hotgraph_stream` tests (one per
    collector), which resolve each fixture profile all the way through
    `resolve_stream`/`HitStream`.
(b) "an unparseable profile errors naming the file" -- proven by
    `test_unparseable_profile_errors_naming_the_file` (perf, JFR) and
    `test_invalid_json_errors_naming_the_file` /
    `test_missing_required_keys_errors` (V8).
(c) "unattributed weight is reported as a visible fraction" -- proven by
    `test_frame_with_no_debuginfo_is_unattributed_not_dropped` and
    `test_unmapped_class_is_unattributed_not_dropped`.
(d) "deciles readable per language" -- checked the T-0710 hot-graph
    surface (`src/frob/perf/_hotgraph.py`: `HitStream`, `SectionHit`,
    `EdgeHit`, `unattributed_weight`) and the store ticket, T-0711
    ("hot-graph sketch store: log-bucket quantile sketches ... deciles/
    any-quantile computed at read time"): T-0711 is `state: queued`,
    not built. There is no decile/percentile readout anywhere in this
    codebase today (`grep -rn "decile\|percentile" src/frob/` is empty)
    -- clause (d) genuinely cannot be satisfied by this ticket's own
    scope (collector adapters only; the store that computes deciles is
    T-0711's job, gated behind it in the dependency chain).

Per the coordinator's option 2: criterion [0] stays worded as-is (not
split into a new criterion, since `frob ticket` has no acceptance-text-
edit verb -- `frob ticket --help` lists only `evidence --accepts INDEX`
for binding, no rewrite/split command) and is bound via
`frob ticket evidence T-0748 <3 node ids> --accepts 0` to the three
`test_resolves_through_shared_hotgraph_stream` tests, which are the
existing resolve_stream round-trip proof already covering (a)/(b)/(c).
This is a CRITERION-SPLIT disclosure, not a satisfaction claim: clause
(d) "deciles readable per language" is NOT proven by this evidence and
is NOT claimed to be. Clause (d) is discharged by T-0765, whose
acceptance text literally reads "per-language deciles are readable from
the CLI output" -- T-0765 is the live-invocation/CLI-wiring follow-up
already disclosed above (not filed by this worktree; opened by the
coordinator directly on main, not yet visible in this worktree's own
ledger snapshot).

Evidence (all 15 collected via a fresh pytest --collect-only pass,
tests/unit/perf/test_collectors.py):
TestParsePerfScript::test_parses_committed_fixture_into_leaf_first_stacks,
test_frame_with_no_debuginfo_is_unattributed_not_dropped,
test_unparseable_profile_errors_naming_the_file,
test_resolves_through_shared_hotgraph_stream;
TestParseV8CpuProfile::test_parses_committed_fixture_walking_parent_chain,
test_weight_comes_from_time_deltas, test_invalid_json_errors_naming_the_file,
test_missing_required_keys_errors, test_resolves_through_shared_hotgraph_stream;
TestBuildClassToFile::test_maps_unambiguous_class_to_its_file,
test_class_seen_in_two_files_is_dropped_not_guessed;
TestParseJfrPrint::test_parses_committed_fixture_into_leaf_first_stacks,
test_unmapped_class_is_unattributed_not_dropped,
test_unparseable_profile_errors_naming_the_file,
test_resolves_through_shared_hotgraph_stream.

### Changed
```
 .frob-release.json                           |   7 +-
 docs/guides/extending/test-runner-entries.md |  37 +++
 docs/modules/perf.md                         |  75 +++++-
 pyproject.toml                               |   2 +-
 src/frob/perf/_collectors.py                 | 388 +++++++++++++++++++++++++++
 src/frob/testing/_models.py                  |   7 +-
 src/frob/testing/_runners.py                 |  15 ++
 tests/unit/perf/fixtures/sample.cpuprofile   |  21 ++
 tests/unit/perf/fixtures/sample.jfr.txt      |  18 ++
 tests/unit/perf/fixtures/sample.perf.script  |  11 +
 tests/unit/perf/test_collectors.py           | 237 ++++++++++++++++
 tickets.md                                   | 186 ++++++++++++-
 uv.lock                                      |   2 +-
 13 files changed, 996 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/perf/test_collectors.py::TestParsePerfScript::test_parses_committed_fixture_into_leaf_first_stacks` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParsePerfScript::test_frame_with_no_debuginfo_is_unattributed_not_dropped` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParsePerfScript::test_unparseable_profile_errors_naming_the_file` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParsePerfScript::test_resolves_through_shared_hotgraph_stream` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_parses_committed_fixture_walking_parent_chain` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_weight_comes_from_time_deltas` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_invalid_json_errors_naming_the_file` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_missing_required_keys_errors` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_resolves_through_shared_hotgraph_stream` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestBuildClassToFile::test_maps_unambiguous_class_to_its_file` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestBuildClassToFile::test_class_seen_in_two_files_is_dropped_not_guessed` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseJfrPrint::test_parses_committed_fixture_into_leaf_first_stacks` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseJfrPrint::test_unmapped_class_is_unattributed_not_dropped` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseJfrPrint::test_unparseable_profile_errors_naming_the_file` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseJfrPrint::test_resolves_through_shared_hotgraph_stream` (pytest node id, verified passing when recorded)
