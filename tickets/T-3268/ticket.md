---
id: T-3268
title: 'frob perf spawns a hardcoded bare ''python'' instead of sys.executable: wrong
  interpreter or outright SpawnFailed for real users'
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/perf/_profile.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-28 on main (8a229c515) while re-running the failing node ids
from the 2026-08-28 CI run.

`src/frob/perf/_profile.py::_harness_argv` builds its spawn argv with a
HARDCODED literal interpreter name:

    harness = Path(__file__).parent / "_harness.py"
    script_argv = list(argv)
    if script_argv and script_argv[0] in ("python", "python3"):
        script_argv = script_argv[1:]
    return ["python", str(harness), str(pstats_path), *script_argv]

`sys.executable` appears ZERO times anywhere in `src/frob/perf/` (measured:
`git grep -c sys.executable -- src/frob/perf/` matches no files).

The function's own docstring says "A caller-supplied leading
'python'/'python3' is stripped since the harness supplies the interpreter."
That sentence is not true of this code: the caller's interpreter choice is
stripped and then replaced with a hardcoded guess, not with the harness's own.

OBSERVED FAILURE, two tests:
    tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_profile_then_heat_shows_hot_function
    tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_heat_json_output_is_valid_json
both failing with:
    ERROR: profile_command: ['python', '.../src/frob/perf/_harness.py', ...]
           produced no pstats artifact
    ERROR: profile failed: SpawnFailed: Profiled command could not be started

On this box `python` resolves to /usr/bin/python -- the SYSTEM interpreter,
which does not have frob or its dependencies installed. The harness starts
under the wrong interpreter and produces no pstats.

WHY THIS IS A PRODUCT DEFECT AND NOT A TEST-ENVIRONMENT QUIRK. It has three
distinct failure modes for real users, and the owner is preparing a PyPI
publish, so these ship:
  1. NO `python` ON PATH AT ALL. Common on Windows (where the name may be `py`
     or a Store alias that is not a real interpreter) and on Linux
     distributions that ship only `python3`. `frob perf` fails outright with a
     SpawnFailed that names an interpreter the user never chose.
  2. WRONG INTERPRETER. Where `python` exists but is not the one running frob
     -- a venv, a uv tool install, pyenv, conda -- the profile is taken of a
     DIFFERENT environment than the one under test. That is worse than
     failing: it produces a plausible-looking profile of the wrong thing.
  3. It silently contradicts this repo's own PLATFORM001 doctrine, which is to
     DECLARE a platform boundary rather than degrade quietly.

THE FIX IS ALMOST CERTAINLY `sys.executable`, but VERIFY rather than assume --
check whether any caller deliberately wants a different interpreter (a
cross-interpreter profiling case would be a real reason, and if one exists it
should be an explicit parameter, not a PATH lookup). State what you found.

CHECK FOR SIBLINGS AND REPORT THE COUNT, DO NOT FIX THEM ALL HERE: grep the
whole of `src/` for subprocess argv lists whose first element is a literal
"python"/"python3" rather than `sys.executable`. `frob.perf` is unlikely to be
the only place. Report them so they can be filed individually.

DO NOT FIX THIS BY MAKING THE TESTS SKIP WHEN `python` IS MISSING. The tests
found a real defect; skipping them would delete the detector and ship the bug.

ACCEPTANCE
- The spawned interpreter is the one running frob, or an explicitly chosen
  one, never a bare PATH lookup.
- The two named tests pass without their environment being special-cased.
- A must-fire fixture: with no `python` on PATH (or one shadowed by a
  non-frob interpreter), profiling still works.
- The docstring corrected -- it currently describes behaviour the function
  does not have.
- A stated count of sibling hardcoded-interpreter spawn sites in src/.
