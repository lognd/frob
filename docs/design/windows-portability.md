# Windows portability boundary (T-3076/T-3425)

One sentence: `windows-latest` in `ci.yml` is a real, running, reported
CI leg that is deliberately advisory -- it cannot flip the workflow's
overall conclusion -- until a tracked, characterized set of Windows-only
failures is drained.

## Why this boundary exists

T-3076 characterized 278 Windows-only test failures rooted in five
missing POSIX primitives that this codebase currently assumes are
available everywhere: `fcntl`, `os.sysconf`, `AF_UNIX`, POSIX `fork`
process-start context, and the Windows charmap codec's narrower default
encoding. Closing that set is an epic-sized effort (T-2963's daemon
transport work, plus T-3076's own characterization and follow-on fixes),
not something a CI gate can hold a release on today.

Before T-3425, `windows-latest` was a normal, blocking matrix leg.
Measured on GitHub Actions run 33277131782 (HEAD `bb5c28203`,
2026-08-29), it failed at ~2% of the suite
(`SUITE-RESULT: DID-NOT-COMPLETE exitstatus=2 (INTERRUPTED) collected=12655`,
4 failures before the interrupt); the previous run (33169097371)
completed with 24 failures. Either way `ci.yml`'s overall conclusion was
RED on essentially every push regardless of `ubuntu-latest`/
`macos-latest` health, so `scripts/verify_release_ci_status.py` (T-3251)
could never resolve GREEN and every release needed the `override_red_ci`
escape hatch -- which makes the escape hatch the normal path and
destroys its audit value (PLATFORM001 doctrine:
docs/modules/gates.md#platform001-posix-only-primitive-degrades-silently-t-2919
-- declare a platform boundary explicitly, never silently degrade
around it).

## What T-3425 changed

`.github/workflows/ci.yml`'s `build` job carries
`continue-on-error: ${{ matrix.os == 'windows-latest' }}` at the job
level. Concretely:

- `windows-latest` still runs the full suite, on every push, exactly as
  before -- the signal is kept so the T-3076 burn-down can be measured
  against real CI history, not just local runs.
- A `windows-latest` failure no longer fails the `build` job or the
  overall `ci.yml` workflow conclusion.
- `ubuntu-latest` and `macos-latest` are unchanged: a failure on either
  still fails the workflow, exactly as before this ticket.
- `scripts/verify_release_ci_status.py` (docs/guides/release.md#decision-4-verify-ci-status----ci-must-be-green-for-the-released-commit-t-3251)
  therefore reads GREEN off `ubuntu-latest`/`macos-latest` health; a red
  `windows-latest` leg is a known, tracked gap that does not need
  `override_red_ci` to release.

## Re-measurement after the five primitive fixes (T-3511)

T-3511 re-measured `windows-latest` after all five T-3505 primitive
fixes landed (T-3506 portable locks at `0cebc2819`; T-3508 AF_UNIX;
T-3510 charmap->utf-8; T-3507/T-3509 already-resolved, no in-scope
fix needed). The newest completed run at the time, 33353658750 (HEAD
`2654ca1ff`, 2026-08-31), again **DID NOT COMPLETE**:

```
SUITE-RESULT: DID-NOT-COMPLETE exitstatus=2 (INTERRUPTED) collected=12924 (partial) failed=3 (partial, lower-bound)
```

Only ~1% of the suite ran (129 of 12924 collected) before a bare
`KeyboardInterrupt` killed the whole pytest session at
`threading.py:359`, ~49s after xdist finished bringing up its workers
(03:26:42 -> 03:27:31) -- nowhere near the step's own 1500s (25m)
`Wait-Process` budget or pytest-timeout's `--timeout=120` per-test
threshold, and not attributable to any of the five primitives above.
Per T-3076's own acceptance criterion ("a completed, not-interrupted
Windows run with a stable count"), this non-completion is itself the
finding -- **the 278/365-shaped failure-count baseline this doc
previously carried is retired**; the dominant Windows blocker is now
this early interrupt, not a large stable failure set.

Diagnosis (from job id 99371614987's log): pytest-timeout's
`--timeout-method=thread` was ruled out directly by reading
`pytest_timeout.py`'s `timeout_timer` function -- on expiry it dumps thread stacks
and calls `os._exit(1)`, a hard process exit, never an interrupt
signal; no test in this run ran anywhere near 120s regardless (the
whole session lasted 49s). No `os.kill(CTRL_C_EVENT)` /
`GenerateConsoleCtrlEvent` call exists anywhere under `tests/` or
`src/`. Leading hypothesis: `.github/workflows/ci.yml`'s windows Test
step (T-3250) launches pytest via
`Start-Process -FilePath uv -ArgumentList run,pytest,-q -NoNewWindow -PassThru`
then `Wait-Process -Timeout $budget` -- `-NoNewWindow` means the child
does not get its own console/process group, so it shares the parent
pwsh step's console; a console control event delivered to that shared
console (GitHub-hosted Windows runners are known to broadcast
`CTRL_BREAK_EVENT` to their console as part of heartbeat/cancellation
handling) propagates to every process attached to it, and CPython's
default Windows console-control handler maps that to a
`KeyboardInterrupt` on the main thread -- exactly the observed
`threading.py:359` stack. Filed as a leaf under T-3505 (see table
below); not fixed in T-3511 itself (docs-only scope).

The 3 failures visible before the interrupt were all
`tests/gates/test_comment_placement.py` (Cplace symref/`os.sep`
issue, already noted below) -- also filed as its own leaf.

## Primitive bucket status (T-3076's five buckets)

| Primitive | Failures (of 278) | Status | Ticket |
| --- | --- | --- | --- |
| `fcntl` | 22 (largest, dominates by file -- see T-3506's own body for the by-file breakdown) | open | T-3506 |
| `os.sysconf` | 12 | already guarded on main (`sys.platform != "win32"` wraps the call in `_read_uptime_and_clk_tck`) -- no AttributeError reachable | T-3507 (failed: already resolved) |
| `AF_UNIX` | 10 | guard already correct-direction on main (T-2961); added structural win32-refusal tests (`query`/`probe_daemon`) that were missing | T-3508 (landed) |
| POSIX `fork` start-method | 8 | no hardcoded `get_context("fork")` in T-3509's scoped source files; the literal call sites are all in test harnesses outside scope (some owned by T-3506) | T-3509 (failed: no in-scope fix) |
| charmap codec | 2 | closed -- `tests/test_vet.py`'s two bidi-override tests now pass `encoding="utf-8"` explicitly to `write_text` | T-3510 (this ticket) |

Only the charmap bucket is fully closed by this table's own edits; the
other four rows above are a snapshot from working T-3507/T-3508/T-3509
in the same series as T-3510, not new burn-down from that ticket
itself -- see each ticket's own Done report / Failure log entry for the
measurement backing its row. All five are DONE as of T-3511's
re-measurement (T-3506 landed at `0cebc2819`).

## New failure buckets (post-primitive-fix, T-3511)

The 278/365-shaped counts above are retired as the reference baseline
(see "Re-measurement" above) -- the suite has not completed since, so
there is no comparable stable count yet. Two buckets are characterized
from what DID run before the interrupt:

| Bucket | Shape | Status | Ticket |
| --- | --- | --- | --- |
| Early session-wide `KeyboardInterrupt` | Suite aborts at ~1% (49s in), unrelated to any per-test/step timeout; console-sharing (`Start-Process -NoNewWindow`) hypothesis | open, diagnosed not fixed | T-3540 |
| Cplace symref/`os.sep` | `str(path)` at `_comment_placement.py:179,278` uses the platform separator instead of posix -- 3 failing tests (`TestCplace001`/`TestCplace002`) | open, root cause pinpointed to two exact lines | T-3539 |
| `tests/system/test_ci_hang_guard_positive_control.py` `timeout` mismatch | GNU `timeout` vs Windows `timeout.exe` (`Invalid syntax`) | open (carried over from the 33277131782 measurement; not re-confirmed this run since the suite aborted before reaching it) | untracked -- file when re-measured post-interrupt-fix |

The KeyboardInterrupt bucket blocks measuring anything past ~1% of the
suite, so it is the priority: until it is fixed, no run can produce a
comparable failed-count for the remaining ~99% of the suite, Cplace and
`timeout.exe` included.

## Removing the advisory flag

Remove `continue-on-error` from the `windows-latest` leg (and tighten
the "what green means" note in docs/guides/release.md) once T-3076's
Windows-only failure set reaches zero AND a windows-latest run reaches
a stable, completed (not INTERRUPTED) result -- currently blocked on
the KeyboardInterrupt bucket above, which must be fixed before the
suite can even finish collecting a real failure count to drain. That
removal should land as an explicit acceptance line on T-3076 itself,
not edited into T-3076's body from this ticket.
