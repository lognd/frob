## Done report

Approach: measured first (a single unchunked `--stamp-baseline` on this repo:
~187s wall / ~172s inside `run_gates` alone -- confirms the ticket's premise).
Tried running every gate chunk back-to-back inside ONE process/CLI call first
(reusing the `gates-fast`/`gates-native`/`gates-security` `--only` groups
internally) -- measured WORSE (~240s wall, since `_load_inputs` reloads per
chunk) and still one long foreground command, so this does not solve the
problem and was discarded as the final design (kept only as the documented
coordinator-only bare-invocation fallback, matching the `make coverage`
precedent in playbook section 6b). Final design: `--stamp-baseline --only
<group-or-gate>` (repeatable, same `--only` semantics `frob check` already
has) now runs and records just the requested gate chunk into a new scratch
accumulator (`.frob/baseline-chunks.json`, JSON-serialized `Violation`
models keyed by the chunk's sorted gate ids); the moment the union of every
recorded chunk's gates covers every gate that exists, the merged violations
are handed to the real `frob.gates.stamp_baseline` (still the sole writer of
`.frob/baseline`) and the scratch file is deleted. This lets an agent build
the exact same baseline the old one-shot call produced via N separate,
individually-cheap CLI invocations instead of one that exceeds the cap.
Playbook section 3b/6 updated to document the bare-invocation-is-
coordinator-only rule and the exact chunked recipe (including splitting
`gates-fast` further by individual gate id under contention, since it is the
largest single group and measured as high as ~144s under load in this
session).

Before/after timing (measured on this repo, this session):
- Before (single unchunked `--stamp-baseline`): 187.115s wall
  (`run_gates: done in 172.348s`).
- After, per-chunk (`--stamp-baseline --only <group>`, each its own CLI
  call): `gates-native`+`gates-security` combined ~22s; `gates-fast` split
  into `test` alone plus the rest, or run as one `gates-fast` chunk (~87s
  unloaded, measured up to ~144s under concurrent-agent load this session --
  still requires splitting further under contention, documented). Every
  individual invocation observed in this session completed well inside the
  ~120s cap except one `gates-fast` run under heavy concurrent load, which
  the playbook now calls out explicitly with the finer per-gate split as the
  fix.

Files changed:
- src/frob/app/check_runner.py (`_stamp_baseline_gate_chunks`,
  `_baseline_chunks_path`, `_load_baseline_chunks`, `_save_baseline_chunks`,
  `_resolve_baseline_only_chunk`, rewritten `_run_stamp_baseline`)
- docs/guides/agent-playbook.md (sections 3b and 6 updated: bare
  `--stamp-baseline` is now coordinator-only, documented `--only`-chunked
  recipe for agents)
- tests/unit/test_app_runners_batch6.py (2 new tests; scope extended to
  cover this file, see scope_changes above)

Test evidence (all passed, `-n0`, foreground):
```
uv run pytest tests/unit/test_app_runners_batch6.py -q -n0
........................................................ [100%]  (56 passed)
```
Node ids recorded as evidence:
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_mode_calls_stamp_and_returns
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_gate_error_exits_1
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps

`uv run frob test` (touched-set): `[PASS] python exit=0 3.63s`.

Filed: none.

Gates: `uv run frob check --ticket T-0751 --only <group>` clean for every
group (lint, static, gates-fast, gates-native, gates-security) after
extending scope to include the new test file (SCOPE001 fixed via `frob
ticket scope --add` + `frob ticket sweep`). No waivers added by this
change.

Real baseline state: `.frob/baseline` was actually (re)stamped end-to-end
via the new chunked `--only` flow during verification (4166 violations
across 656 files, matching the pre-existing full-repo violation count),
confirming the merge-and-complete path works against the live repo, not
just mocked unit tests.
