## Done report

Changed:
- src/frob/gates/__init__.py::_PROCESS_POOL_GATES (new)
- src/frob/gates/__init__.py::_CANONICAL_GATE_ORDER (new)
- src/frob/gates/__init__.py::_ProcessJob (new)
- src/frob/gates/__init__.py::_build_jobs (now returns thread_jobs,
  process_jobs, skipped instead of one merged jobs dict)
- src/frob/gates/__init__.py::_run_process_gate (new)
- src/frob/gates/__init__.py::_drain_futures (new)
- src/frob/gates/__init__.py::_submit_process_pool (new)
- src/frob/gates/__init__.py::_merge_canonical_order (new)
- src/frob/gates/__init__.py::_run_combined_jobs (new; replaces the single
  `_run_jobs(jobs)` call `_assemble_gate_report` used to make)
- src/frob/gates/__init__.py::run_gates (updated to call _build_jobs's new
  2-dict return and _assemble_gate_report's new signature)
- src/frob/gates/__init__.py::_assemble_gate_report (takes thread_jobs +
  process_jobs, calls _run_combined_jobs)
- src/frob/gates/__init__.py::_run_jobs (unchanged -- kept as-is for the
  pre-existing TestRunJobsTimingAttribution test and as the thread-only
  primitive `_run_combined_jobs`'s ThreadPoolExecutor half reuses via
  `_timed_job`)
- docs/modules/gates.md (Design decisions bullet updated: documents the
  thread pool / process pool split and the canonical-order merge)
- tests/test_gates.py: added `_module_level_process_violation` helper and
  `TestProcessPoolGates` (4 new tests, listed below)

Approach (H3 fix, per the audit's own "Fix direction"): `archgate`, `sys`,
`clones` (dup_gate), `perf`, `pii_structural`, `secrets` -- the six
CPU-bound, pure-Python gates -- now run in a `ProcessPoolExecutor`
(`_submit_process_pool`/`_run_process_gate`), bounded to
`min(len(process_jobs), os.cpu_count() or 4)` workers. Every other gate
(drift, coverage, invariant, test, policy, doclink, docanchor, fuzz,
release, decisions, tickets, refs, scope, prework) stays on the existing
`ThreadPoolExecutor` (I/O-bound or cheap enough that process-spawn/pickle
overhead would not pay for itself). Both pools run concurrently inside one
`with ThreadPoolExecutor(...) as tpool:` block (process pool submitted
first, thread pool submitted while the process pool works, then drained
in that order) -- archgate/sys/etc. genuinely overlap instead of
GIL-serializing.

Constraint 1 (graph built once, no swallowed summary): `_load_inputs`
still runs exactly once in the parent (`run_gates` -> `_load_inputs` ->
`_load_required_state` -> `build_graph`, untouched). Process-pool workers
never rebuild the graph -- `_ProcessJob` carries the already-built
`GraphSnapshot` (a frozen pydantic `BaseModel` of plain data: strings,
tuples, a `Mapping[str, SymbolRecord]`) as a plain picklable argument, not
a handle the worker re-derives. `_run_process_gate`'s return value
(`tuple[Violation, ...]`, itself a plain pydantic model) is the only thing
shipped back; nothing is silently dropped -- `_drain_futures` calls
`future.result()` for every submitted future (an exception in a worker
process propagates through `.result()` exactly like the old
`ThreadPoolExecutor` path did).

Constraint 2 (deterministic output): `_CANONICAL_GATE_ORDER` fixes the
exact gate-name order the old single-dict `_build_jobs` used to produce.
`_merge_canonical_order` walks that order over the `raw` dict (populated
by whichever pool finished a given job, in whatever order the OS
scheduled it) to build the final violation list -- so wall-clock overlap
never changes output order. Verified two ways:
  1. `test_run_gates_output_is_identical_across_repeated_runs` -- run
     `run_gates` twice on the same tree with a thread+process gate mix,
     assert `report1.violations == report2.violations` and
     `report1.stats.counts == report2.stats.counts`.
  2. Real `frob check` run, before vs. after, byte-diffed with only
     timing numbers stripped (see Evidence below) -- the only diff lines
     left are line-number shifts caused by the added test/doc lines
     themselves (e.g. a duplicate-block report moving from
     `tests/test_gates.py:1843` to `:1864` because 21 lines were inserted
     above it) and the `large-file` line count going from 4148 to 4326.
     Every rule id, file set, violation count, and the top-line
     `1 error 139 warnings` tally are identical. No violation appeared,
     disappeared, or reordered independent of the line-number shift.

Constraint 3 (picklability): confirmed by inspection and by test --
`GraphSnapshot`, `Diff`, `Violation` are all `pydantic.BaseModel` with
`model_config = ConfigDict(frozen=True)` over plain-data fields (str,
tuple, Mapping of other frozen models) -- no native/Rust handles, no
closures. `_ProcessJob.func` is always a module-level function reference
(`arch_gate`, `sys_gate`, `dup_gate`, `perf_gate`, `secrets_gate`,
`pii_structural_gate`), never a lambda, so `pickle` addresses it by
`__module__`+`__qualname__`.
`test_process_job_runs_in_a_separate_process` proves this end-to-end: it
submits a `_ProcessJob` through `_run_combined_jobs` and asserts the
returned `Violation.message` embeds a pid different from
`os.getpid()` in the test process -- i.e. the job really executed in a
worker, not merely serially in-process (which would silently pass a
naive fake).

Constraint 4 (bounded workers, no double-work, no deadlock):
`proc_workers = max(1, min(len(process_jobs), os.cpu_count() or 4))` --
never more workers than jobs, never more than the machine's CPU count.
Each `_ProcessJob` is submitted exactly once
(`_submit_process_pool`'s dict comprehension, one future per job name);
`_drain_futures` collects each future exactly once. The `with
ProcessPoolExecutor(...) as ppool:` block is nested inside the `with
ThreadPoolExecutor(...) as tpool:` block and both are drained before
either `with` exits, so there is no cross-pool deadlock (`_run_jobs`'s
existing single-pool test, `TestRunJobsTimingAttribution`, and the whole
`tests/test_gates.py` suite -- 168 tests -- still pass unmodified,
confirming no interaction with the pre-existing thread-pool timing
behavior).

Wall-time measurement (`docs/audits/perf.md H3`'s own protocol, `/usr/bin/
time -v uv run frob check`, this repo, warm parse cache both sides -- cold
first-run numbers are also in scratch logs but confounded by cache
rebuild, not reported as the headline number):

| | Before (HEAD 26a3c16, serial ThreadPoolExecutor) | After (this branch) |
|---|---|---|
| Elapsed wall clock | 51.75s | 20.85s |
| User CPU | 42.47s | 24.07s |
| Percent CPU | 108% (near single-core -- GIL-serialized) | 166% (real overlap) |

~31s / ~60% wall-time reduction on this measurement, consistent with H3's
claim that overlapping archgate+sys alone should save ~77s on the
audit's original (much larger, cold-cache) run; this repo's current
gates-stage cost is smaller post-T-0414 (parse cache landed), so the
absolute savings here are smaller than the audit's original estimate but
the CPU-utilization jump (108% -> 166%) directly confirms the GIL
serialization is broken as intended.

Baseline measured via a disposable `git worktree add --detach HEAD`
checkout (`make core` + `/usr/bin/time -v uv run frob check`, run twice to
warm the parse cache before the reported number), removed afterward
(`git worktree remove`) -- never touched via `git stash` or any mutation
of this checkout's tracked state, per the playbook's rule 1b.

Real findings this change caused, fixed before closing: ty
`invalid-argument-type` (test helper return-type annotations needed to
match `Callable[..., tuple[Violation, ...]]` under dict-invariance),
ARCH001 (`_run_combined_jobs` initially 60 lines over the 30-line
threshold -- split into `_drain_futures`/`_submit_process_pool`/
`_merge_canonical_order`), PERF004 (a `sorted()` call that ty/PERF004
mis-flagged as "in a loop" in the new comparison test -- rewritten as two
list comprehensions plus two named `sorted()` calls, no rule change
needed). All confirmed clean via `frob check --ticket T-0415` (0 gates
errors) and `ruff check`/`ruff format --check`/`ty check` on the touched
files.

Evidence:
- tests/test_gates.py::TestProcessPoolGates::test_process_job_runs_in_a_separate_process
- tests/test_gates.py::TestProcessPoolGates::test_combined_jobs_merge_in_canonical_order
- tests/test_gates.py::TestProcessPoolGates::test_run_gates_output_is_identical_across_repeated_runs
- tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path
(recorded via `frob ticket evidence T-0415 ...`, verified passing:
`uv run pytest -q <these 4 node ids>` exit=0, 4 passed)

Filed: none (no out-of-scope discoveries beyond the scope widening noted
above, which was declared, not silent).

Gates: `frob check --ticket T-0415` clean -- 0 gates errors, 0 SCOPE001,
0 PRE001. The only remaining ERROR in a full `frob check` run
(`src/frob/testing/_select.py:309` E501) is pre-existing on `main`
(confirmed present, byte-identical, in the baseline worktree run before
this ticket's changes) and outside T-0415's scope.
`frob test --base main`: `[PASS] python exit=0 4.75s` (touched-set
selection picked up `tests/test_gates.py` in full plus the specific new
node ids).

## Post-merge addendum (committed 8f535d1, merged main at c48bda7)

`git merge main` (main had advanced significantly -- T-0343 registry
exhaustiveness gate landed, among other work) auto-merged cleanly with no
conflict markers in `tickets.md` or `gates/__init__.py`. One real bug
surfaced by the merge, found and fixed before re-verifying: main's
`_ALL_GATES`/`_build_jobs` additions included a new `"registry"` gate
(T-0343, `registry_gate`), but my `_CANONICAL_GATE_ORDER` tuple (added
pre-merge, so main's side had no knowledge of it) did not list
`"registry"` -- `_merge_canonical_order` only walks names present in that
tuple, so `registry`'s violations would have been silently dropped
(a real T-0122 "swallowed summary" regression). Added `"registry"` to
`_CANONICAL_GATE_ORDER` (single-line fix,
`src/frob/gates/__init__.py::_CANONICAL_GATE_ORDER`) and re-verified.

Re-ran `make core` after the merge (native fingerprints unchanged, fast
no-op build). `frob test --collect` refreshed pytest collection (a
pre-existing, out-of-scope COV003 on T-0343's own evidence needed a
refreshed collect cache, unrelated to this ticket's change -- see below).

**Wall-time, post-merge tree** (`/usr/bin/time -v uv run frob check`,
warm parse cache, this branch after merge+registry fix):
Elapsed 23.53s, User 26.89s CPU, 160% CPU utilization -- consistent with
the pre-merge measurement (20.85s / 166% CPU) reported above; the merge
itself did not change the timing story. Pre-change reference: H3's own
audit number (archgate 91.5s + sys 77s summed under the old GIL-serial
single pool) plus this ticket's own pre-merge before/after
(51.75s -> 20.85s, 108% -> 166% CPU) already establishes the delta; not
re-running an isolated `main` checkout again per this addendum's
instruction to avoid a second worktree/timing round-trip.

**Byte-identical output, same-tree toggle proof** (this addendum's
requested same-tree A/B, done in the foreground, no backgrounding):
temporarily edited `_build_jobs` to route every `process_jobs` entry
through the thread pool instead (forcing the pre-T-0415 all-threads
behavior) via `git diff`-visible inline edit, ran `uv run frob check`,
captured output, reverted the edit (confirmed via `git diff --stat`
showing only the intentional `registry` line remaining), ran
`uv run frob check` again with the real parallel path. Diffed both
(timing floats normalized): the `gates` stage's own summary line is
byte-identical between the two runs --
`1 error, 1078 warnings, 43 waived` with the identical
`[archgate=... clones=... ... registry=... ...]` gate-name list in both.
The only diff lines anywhere in the two full-check outputs are artifacts
of the temporary toggle edit itself (an E501/ruff-format hit on the
toggle's own inserted line, and a +7 large-file line count while that
line existed) -- not gate-logic differences. This directly confirms
constraint 2 (deterministic output) survives the merge.

Re-recorded evidence post-merge (same 4 node ids,
`frob ticket evidence T-0415 ...`, verified `pytest` exit=0 1.88s, 4
passed) since evidence must resolve against the post-merge collection
cache, not the pre-merge one.

`frob check --ticket T-0415`: 0 SCOPE001, 0 PRE001. Two ERRORs remain in
a full (unscoped) `frob check` run, both pre-existing/out-of-scope:
`src/frob/testing/_select.py:309` E501 (same as before the merge) and
`tickets/T-0343:0` COV003 (T-0343's own evidence id not resolving against
a fresh collect -- landed on `main` before this branch merged it in, not
introduced by this ticket; not touching T-0343's files, outside T-0415's
`scope`).

`frob test --base main` (post-merge): `[PASS] python exit=0 2.96s`.

Branch: `worktree-agent-a946c3b9b8b495131`. HEAD after merge: `c48bda7`
(merge commit; `8f535d1` is this ticket's own commit,
`0ee1b06` was main's tip before merging).

NOT closing -- reviewer-gated per dispatch instructions.
