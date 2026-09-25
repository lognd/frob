---
id: T-5480
title: 'Windows-only: dotnet/unity runner tests fail with RunFailed (toolchain/env?)'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
body_changes:
- mode: append
  reason: record in-progress diagnosis before pausing to prioritize the newer CI drain
    run 36086669322
  actor: logan
  at: '2026-09-24'
  old_length: 1298
  new_length: 3911
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19), windows-latest job
only. 4 failing node ids:
- tests/unit/test_dotnet_runner.py::TestRunDotnetTests::test_maps_passing_and_failing_ids
- tests/unit/test_dotnet_runner.py::TestRunDotnetTests::test_requested_id_missing_from_results_is_err
- tests/unit/test_unity_batchmode.py::TestRunUnityBatchmode::test_maps_passing_and_failing_ids
- tests/unit/test_unity_batchmode.py::TestRunUnityBatchmode::test_requested_id_missing_from_results_is_err

All four fail with Err(...RunFailed)/Err(...RunFailed) where the test
expects Ok -- the dotnet/unity runner subprocess itself failed under the
test, not a mapping/parsing bug in the code under test. This LOOKS like a
missing/misconfigured dotnet or Unity toolchain on the windows-latest CI
runner image rather than a code regression -- needs confirmation by
reading the actual captured subprocess stderr (not visible in the
SUITE-RESULT-FAILED short summary this drain pass extracted) before
deciding whether this is a CI image/environment ticket or a real runner
bug. Also relevant: these two files' waivers are the exact ones cluster J
(WIRE002, see the sibling ticket for that cluster) found pointing at
already-done follow-up tickets -- may be related infrastructure drift in
the same two files.


IN-PROGRESS FINDING (measured on the real Windows mirror, not yet fixed --
paused to prioritize the newer CI drain run 36086669322 per coordinator
request):

Unity fixture (_write_fake_unity in tests/unit/test_unity_batchmode.py):
its Windows .cmd script has a real CMD batch bug -- the arg-parsing loop
does `shift` then `set OUT=%~1` together inside one `( ... )` block:

    if "%~1"=="-testResults" (
      shift
      set OUT=%~1
    )

CMD expands %~1 for an ENTIRE parenthesized block at PARSE time, before
any line inside it (including `shift`) executes -- so `set OUT=%~1`
still sees the PRE-shift value (the literal flag "-testResults" itself),
not the path that follows it. Measured directly: running this fixture
produces a file literally named "-testResults" in the working directory
instead of writing the results XML to the intended path, so
run_unity_batchmode always sees "no results file" -> RunFailed. This is
a real, reproducible CMD delayed-expansion bug in the TEST FIXTURE, not
frob's own runner code. Fix needs `setlocal enabledelayedexpansion` +
`!OUT!` (or restructuring to avoid `shift`+`set` sharing one block).

Dotnet fixture (_write_fake_dotnet in tests/unit/test_dotnet_runner.py):
a DIFFERENT, not-yet-root-caused failure -- test_maps_passing_and_failing_
ids gets a literal CMD syntax error ("'FullyQualifiedName' is not
recognized as an internal or external command") when the filter
expression contains a `|` (dotnet's own OR-combinator syntax,
FullyQualifiedName=A|FullyQualifiedName=B) -- consistent with Windows
CreateProcess re-invoking a .cmd target through cmd.exe's own shell
grammar, which then reinterprets `|` as a CMD pipe operator even though
it arrived as one argv element. test_requested_id_missing_from_results_is_
err (single filter term, no `|`) fails differently ("exited 0 with no TRX
file") -- reproduced directly via run_argv with a single-filter argv:
rc=0, no stdout, no TRX written -- the dotnet.cmd fixture's own findstr-
based arg-matching silently fails too, root cause not yet isolated (ran
out of time before pivoting).

Both are TEST-FIXTURE bugs (not frob's own _dotnet_runner.py/_unity_
batchmode.py runner code, which behaves correctly given a well-formed
results file), specific to how these two hand-rolled Windows .cmd shims
parse dotnet/Unity CLI argv shapes. A dedicated pass rewriting both
fixtures (with `setlocal enabledelayedexpansion` for Unity's, and
verifying dotnet's `|`-separated filter survives a .cmd round-trip, or
switching to a `.ps1`/python-based shim entirely instead of hand-rolled
CMD batch) would close this cluster.
