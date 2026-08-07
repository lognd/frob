## Done report

Delivered the T-0710 stream contract, resolver, python sampler, plus the
review-round-2 fixes below (silent mis-attribution, harness wiring,
acceptance binding).

## Stream contract, resolver, sampler (round 1, unchanged)

Stream contract (`src/frob/perf/_hotgraph.py`): `SampledFrame(file, line)`
and `SampledStack(frames, weight)` -- the language-neutral hit-stream unit,
nothing python-specific, per the CONTRACT MANDATE. `SectionHit`/`EdgeHit`/
`HitStream` are the resolver's output for T-0711's sketch store.
`HitStream.unattributed_weight` surfaces samples matching no section
(NO-FAIL-SILENT: never dropped).

Python sampler (`src/frob/perf/_sampler.py`): `StackSampler` runs a
background daemon thread reading `sys._current_frames()` every
`SamplerConfig.interval_s` (10ms default); `run_sampled(fn, config)`
brackets a callable like `cProfile.Profile.enable`/`disable`.

## Round 2 fix 1 (BLOCKING): degrade-to-correct block spans

The reviewer proved the round-1 next-sibling-boundary approximation
silently mis-attributed: `NormalizedLoop`/`NormalizedBranch` are FLATTENED
sibling lists with no nesting info, so a branch nested inside a loop had
its guessed span reach all the way to the function's end (nothing else
claimed those lines) -- a sample taken in the LOOP's body AFTER the branch
resolved to the WRONG branch section, not unattributed, wrong-and-silent.

Fix in `src/frob/perf/_hotgraph.py::_block_sections`: a block only gets an
EXTENDED span (its anchor line to the function's end) when it is PROVABLY
the function's only loop/branch (`len(blocks) == 1`) -- no sibling/nested
ambiguity possible. The instant a function has 2+ loops/branches, EVERY
block in it degrades to a single-line span (`start_line == end_line`, its
own anchor only); any other line in that function resolves to the
enclosing FUNCTION section instead of a guessed sibling -- coarser, never
wrong.

New regression test:
`tests/unit/perf/test_hotgraph.py::TestResolveStream::
test_loop_body_after_nested_branch_never_attributes_to_branch` -- a
loop-with-nested-branch fixture (loop anchor line 2, branch anchor line 3,
more loop-body lines at 4-6), run across TWO languages (python, cpp) to
keep proving the fix is language-neutral. Asserts the branch section is a
single line and a frame at line 5 (loop body after the branch) resolves to
something other than the branch -- specifically the loop or the function,
never the branch.

Documented in the module docstring, `_block_sections`'s own docstring, and
`docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709`.

## Round 2 fix 2: perf harness wiring

`src/frob/perf/_harness.py` now wires the sampler in: setting
`FROB_PERF_SAMPLE=1` in the environment runs a `StackSampler` alongside
cProfile (started/stopped bracketing the same `try`/`finally` cProfile
already uses) and, in the `finally` block, resolves the collected
`SampledStack`s against a best-effort `SectionIndex` (parses just the
distinct python files the samples actually touched, via
`frob.lang.raw_tree` + `frob.arch._python.PythonAdapter` -- not a
repo-wide parse) and logs a `hotgraph: N sample(s), M section(s) hit,
top=[...], unattributed_weight=..., edge_hits=...` summary line.
Deliberately a LOGGED summary, not a persisted artifact -- T-0711's
sketch store does not exist yet; this is the first real caller of
`resolve_stream` outside its own test suite, proving the contract
composes with an actual subprocess-shaped run. Off by default (opt-in env
var), so the unsampled path (and every existing `frob perf profile` call)
is provably unaffected.

New tests in `tests/unit/perf/test_harness_sampling.py::
TestHarnessSampling`: `test_unsampled_run_is_unaffected` (baseline: clean
exit code, pstats file written, no hotgraph log line when the env var is
unset), `test_sampled_run_logs_hotgraph_summary` (env var set: workload
still exits clean and writes pstats, AND exactly one `hotgraph:` log line
appears with `unattributed_weight=` and a sample count), and
`test_sampled_run_resolves_the_hot_loop_section` (the logged sample count
is nonzero, proving `resolve_stream` actually ran against the fixture
script's own parsed module, not an empty stream).

## Round 2 fix 3: acceptance binding

`acceptance[0]` was previously UNBOUND. Bound via `frob ticket evidence
T-0710 <node-id> <node-id> --accepts 0` (the two tests most directly
proving the acceptance text -- "a hot inner loop calling an external
function" attributing correctly and staying under the overhead budget):
`TestResolveStream.test_loop_body_after_nested_branch_never_attributes_to_branch`
and `TestStackSampler.test_overhead_under_five_percent`. Confirmed via
`frob ticket show T-0710`: `[0] bound([...]): GIVEN a fixture with a hot
inner loop...`.

## Round 2 disclosure 4: REL001 + follow-up ticket

`frob check --ticket T-0710` reports `REL001: public API changed (minor)
since 0.93.0; bump the version to >= 0.94.0` -- NOT bumped in this
worktree (per this dispatch's standing instruction never to touch
version/CHANGELOG files); the coordinator bumps at land.

Filed a real follow-up ticket for the overhead test's own fragility risk:
the follow-up (materializes from provisional id `T-0759 (ex-draft, id lost at land)` at
land, per this repo's off-default-branch id-minting convention; the block
exists in `tickets.md` today and is NOT flagged by `frob check --only
tickets` TICK006, i.e. it is a real, resolvable filing, not a phantom)
tracks hardening `test_overhead_under_five_percent` against
pytest-xdist wall-clock contention (a `serial`/`xdist_group` marker, or a
relaxed CI tolerance) -- the test already uses best-of-3 timing to
suppress ordinary scheduler noise, but xdist worker contention under `-n
auto` is a distinct risk this ticket does not fully rule out.

## Measured overhead (unchanged from round 1)

`TestStackSampler::test_overhead_under_five_percent`: best-of-3 unsampled
vs sampled runs of a 3M-iteration fixture hot loop; measured locally
~0.110s unsampled vs ~0.110-0.113s sampled (7 samples at the 10ms
default) -- comfortably under the 5 percent budget.

## NO-FAIL-SILENT (unchanged from round 1, now also proven under nesting)

`test_unresolvable_leaf_is_unattributed_never_dropped` proves an
unmatched frame still emits a visible `SectionHit(UNATTRIBUTED_SECTION_ID,
weight)`. The round-2 fix extends this guarantee to the AMBIGUOUS-nesting
case too: a frame that cannot be soundly attributed to a specific block
now degrades to the enclosing function (still correct, still visible),
rather than either being dropped or (the round-1 bug) silently assigned to
the wrong block.

### Changed
```
 docs/modules/perf.md                     | 140 +++++++++++
 src/frob/perf/__init__.py                |  33 +++
 src/frob/perf/_harness.py                |  89 ++++++-
 src/frob/perf/_hotgraph.py               | 396 +++++++++++++++++++++++++++++++
 src/frob/perf/_sampler.py                | 179 ++++++++++++++
 tests/unit/perf/__init__.py              |   0
 tests/unit/perf/test_harness_sampling.py |  95 ++++++++
 tests/unit/perf/test_hotgraph.py         | 311 ++++++++++++++++++++++++
 8 files changed, 1242 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/perf/test_hotgraph.py::TestResolveStream::test_leaf_in_loop_body_attributes_to_loop_section` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestResolveStream::test_leaf_in_branch_body_attributes_to_branch_section` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestResolveStream::test_call_edge_classified_external_when_callee_unmodeled` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestResolveStream::test_call_edge_classified_internal_when_callee_modeled` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestResolveStream::test_unresolvable_leaf_is_unattributed_never_dropped` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestResolveStream::test_empty_stack_produces_no_hits` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestStackSampler::test_collects_at_least_one_sample_over_a_hot_loop` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestStackSampler::test_stop_without_start_is_safe_and_empty` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestStackSampler::test_start_is_idempotent` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestStackSampler::test_max_depth_caps_frame_count` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_sampling.py::TestHarnessSampling::test_unsampled_run_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_sampling.py::TestHarnessSampling::test_sampled_run_logs_hotgraph_summary` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_sampling.py::TestHarnessSampling::test_sampled_run_resolves_the_hot_loop_section` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestResolveStream::test_loop_body_after_nested_branch_never_attributes_to_branch` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent` (pytest node id, verified passing when recorded)
