## Done report

## Done report

Changed:
src/frob/gitio.py::SpawnRecorder
src/frob/gitio.py::SpawnRecorder.record
src/frob/gitio.py::SpawnRecorder.counts
src/frob/gitio.py::SpawnRecorder.duplicates
src/frob/gitio.py::spawn_recorder
src/frob/gitio.py::run_argv (one ContextVar.get() hook, no behavior change)
tests/system/test_spawn_budget.py (generalized off raw subprocess.run monkeypatch onto spawn_recorder; seed case kept xfail(strict) + T-0773 tag; 3 new budget cases)
tests/test_gitio.py::TestSpawnRecorder (unit coverage for the new public API)
docs/modules/testing.md (Public API entries + new "Spawn recorder (T-0776)" section)

Evidence (all pass under `uv run pytest tests/system/test_spawn_budget.py tests/test_gitio.py -q`):
tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once (xfail(strict), T-0773-tagged, bound acceptance[0])
tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once (pass, bound acceptance[0])
tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once (xfail(strict), T-0773-tagged -- doable hits the SAME rev-parse --git-common-dir per-ticket-row duplication as list, discovered while implementing; bound acceptance[0])
tests/system/test_spawn_budget.py::test_exclude_hazard_gate_spawns_each_argv_at_most_once (pass, bound acceptance[0])
tests/test_gitio.py::TestSpawnRecorder::* (5 unit cases, unbound -- pure recorder-mechanism tests, no ticket acceptance criterion covers the mechanism itself separately from the CLI-path litmus)

Filed: none (no new tickets opened; the `doable` duplication found is the SAME pre-existing T-0773 bug the ticket already anticipated, not a new discovery)

Gates: `uv run frob check --ticket T-0776` chunked (lint, static, gates-native, gates-security clean; gates-fast's coverage/test/prework/scope stages show zero findings on any file in T-0776's scope -- remaining FAILs in that stage-group are pre-existing debt in src/frob/perf/_collectors.py and src/frob/vet/_capability_modes.py, unrelated files from an already-landed ticket, confirmed via `--only test` output containing no gitio.py/test_spawn_budget.py/test_gitio.py/testing.md lines). No waivers added.

Deviations from the ticket plan:
- `test_ticket_doable_spawns_each_argv_at_most_once` is xfail(strict)+T-0773-tagged rather than a plain pass -- discovered it hits the identical unmemoized `git_common_dir` re-derivation `list` does (both walk leases through the same seam), so per the dispatch instruction ("do not fix the duplication yourself") it stays documented debt alongside the seed case, not silently green.
- Recorder implemented as a `contextvars.ContextVar`-backed context manager directly inside `frob.gitio` (hooked into `run_argv`, the package's one process-with-timeout seam) rather than a raw env-gated counter -- every git spawn in the codebase already routes through `run_argv`, so this needed no call-site changes anywhere else and stays zero-cost (one `ContextVar.get()`) when no recorder is active.
- "check --only fast stages" budget coverage: implemented against `exclude_hazard_gate` (a fast, git-light gates-fast member) rather than a full `check --only fast` run, which spawns hundreds of non-git subprocesses (ruff/ty/native tools) unrelated to the argv-duplication class this litmus targets and would make the test slow/noisy without adding git-spawn-budget signal.

## Reviewer round-1 fixes (REL001 + TEST010, disclosed)

REL001 (undisclosed release stamp): `SpawnRecorder`/`spawn_recorder` are new
public API in `frob.gitio.__all__` and had no release stamp recorded.
Scope-added `pyproject.toml`, `.frob-release.json`, `uv.lock` (reason:
"REL001: new public gitio.SpawnRecorder/spawn_recorder API required a
release stamp; reviewer-directed scope-add"). Ran `uv run --frozen frob
release stamp` (stamped 1337 public symbols at 0.100.0 -> written to
`.frob-release.json`; `pyproject.toml`'s version line was already at
0.100.0 from merging main, no separate bump needed on top of that).
`uv run --frozen frob check --ticket T-0776 --only release` now shows
**zero `gate:REL` findings at all** (the gate does not print a row when
it has nothing to report -- confirmed via `grep -c "gate:REL"` on the
full command output, count 0).

TEST010 (kind divergence from main's landed fix, commit c9d21365): merged
main into this branch (committed WIP first, no stash; one real conflict
in `tests/system/test_spawn_budget.py`, resolved by keeping this
ticket's `spawn_recorder`-based test bodies but adopting main's
`kind="e2e"` for all four `frob:tests` directives in that file, matching
main exactly). `tests/test_perf_loop_invariant_effect_lock.py` (outside
T-0776's own scope, not touched directly) came in already fixed to
`kind="integration"` via the merge itself -- main's landed commit
resolved it, the merge was a clean fast-forward-shaped pickup, no
conflict there. `uv run --frozen frob check --ticket T-0776 --only test`
now shows **zero `TEST010` findings** for either file (`grep TEST010`
on the full stage output: no matches for either filename).
Re-ran `uv run pytest tests/system/test_spawn_budget.py tests/test_gitio.py
tests/test_perf_loop_invariant_effect_lock.py -q` after reconciliation:
all pass (2 xfail, as before -- the T-0773 seed + doable case).

### Changed
```
 docs/modules/testing.md           |  59 ++++++++++++++++
 src/frob/gitio.py                 |  74 +++++++++++++++++++-
 tests/system/test_spawn_budget.py | 137 +++++++++++++++++++++++++++++---------
 tests/test_gitio.py               |  57 +++++++++++++++-
 tickets.md                        |  76 +++++++++++++++++++--
 5 files changed, 366 insertions(+), 37 deletions(-)
```

### Evidence
- `tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/system/test_spawn_budget.py::test_exclude_hazard_gate_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
