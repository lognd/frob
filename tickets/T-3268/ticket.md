---
id: T-3268
title: 'frob perf spawns a hardcoded bare ''python'' instead of sys.executable: wrong
  interpreter or outright SpawnFailed for real users'
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/perf/_profile.py
- tests/test_perf.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_perf.py
  reason: T-3268's fix requires a must-fire regression test proving sys.executable
    is used instead of a bare python PATH lookup
  actor: logan
  at: '2026-08-28'
triage_changes:
- field: priority
  old_value: high
  new_value: critical
  reason: 18 of 60 suite failures trace to this one hardcoded interpreter; largest
    single identified block to a green suite and it ships broken to PyPI users whose
    PATH lacks python
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: append
  reason: full-suite baseline shows this one defect produces 18 of 60 failures across
    three independent chunks -- the largest single block between main and green
  actor: logan
  at: '2026-08-28'
  old_length: 3680
  new_length: 6802
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


THIS ONE DEFECT ACCOUNTS FOR ROUGHLY 30% OF THE ENTIRE SUITE'S FAILURES.
Measured 2026-08-28 against Series DS's full chunked baseline of main
(SHA 50f752835f, 12,530 tests collected, 9 completed chunks, -n 4
--dist=loadgroup).

    total FAILED across completed chunks        60
    FAILED node ids mentioning perf/heat        19
    occurrences of the SpawnFailed signature    18
        chunk1a (tests/unit half A)              9
        chunk3b (top-level third 2)              8
        chunk4c (integration+system)             1

Every one carries the identical signature, and it names the hardcoded
interpreter directly:

    ERROR: profile_command: ['python', '.../src/frob/perf/_harness.py',
           '.../pstats', 'workload.py'] produced no pstats artifact
    ERROR: profile failed: SpawnFailed: Profiled command could not be started
    AssertionError: PerfError.SpawnFailed

The affected files span three separate areas, which is why this looked like
three unrelated problems in the baseline histogram rather than one:
    tests/unit/test_app_runners_batch6.py::TestPerfRunner::*
    tests/test_perf.py
    tests/system/test_cli_perf.py::TestPerfProfileAndHeat::*

Series DS's baseline identified this group as "the largest uncharacterized
mass, unmapped to any ticket, strong single-shared-root-cause candidate" and
correctly declined to guess the cause. The cause is this ticket.

WHAT THIS CHANGES:
  1. Priority. This is no longer one broken feature -- it is the single
     largest identified block between main and a green suite. Of 60 failures,
     4 are owned by T-3249's follow-ups, 6 are a separate closed-but-regressed
     question against T-3041, and 18 are THIS. Fixing it removes more of the
     failure list than everything else currently owned, combined.
  2. Confidence. The original filing rested on 2 failing tests and a code
     read. It now rests on 18 occurrences of one signature across three
     independent chunks of a full-suite measurement.
  3. It does NOT change the diagnosis or the fix. `_harness_argv` returns
     `["python", ...]`; `sys.executable` appears zero times in
     `src/frob/perf/`. Everything in the original body stands.

STILL VERIFY BEFORE FIXING, because a 30% claim deserves it: confirm that all
18 share this one root cause rather than merely sharing a symptom. A
SpawnFailed can in principle have other causes, and this drive has already
produced several confidently-asserted causes that were never checked. If any
of the 18 turn out to be a different defect, say which and file separately.

CI IMPLICATION worth stating in the fix's Done report: these tests were NOT in
the CI failure list the owner pasted, because that run aborted with
exitstatus=3 before reaching most of them. A run that fails early hides how
much is broken. That is the same lesson T-3246 encodes and it is worth naming
here as evidence the two defects compound.

Raw logs: /tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/suite_run/
(chunk1a.log, chunk3b.log, chunk4c.log). Re-run the counts rather than
trusting them second-hand.
