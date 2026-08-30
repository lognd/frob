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

## Concrete failures recorded (not fixed here)

Run 33277131782 surfaced these Windows-only failures; they belong under
T-3076's own burn-down, not this ticket:

- `tests/gates/test_comment_placement.py::TestCplace001::test_symref_binds_to_the_enclosing_function`
  and `test_must_stay_quiet_exempt_path` -- both assert a POSIX-style
  symref path (illustrative shape:
  <!-- frob:waive DOC006 reason="path.py::symbol_name here is an illustrative placeholder shape, not a real tracked file" -->
  a forward-slash `path.py::symbol_name` pair) but Windows produces the
  same pair joined with a backslash instead (`os.sep`-shaped, not
  normalized to posix).
- `tests/system/test_ci_hang_guard_positive_control.py::...::test_ordinary_fast_test_is_unaffected`
  -- shells to `timeout`, which resolves to `timeout.exe` on Windows
  (`Invalid syntax. Default option is not allowed more than '1' time(s)`),
  a different program than GNU coreutils' `timeout`.

## Removing the advisory flag

Remove `continue-on-error` from the `windows-latest` leg (and tighten
the "what green means" note in docs/guides/release.md) once T-3076's
Windows-only failure set reaches zero. That removal should land as an
explicit acceptance line on T-3076 itself, not edited into T-3076's body
from this ticket.
