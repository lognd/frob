---
id: T-2486
title: nothing structurally prevents a stdout write from corrupting --json output;
  T-2484 fixed one instance
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/check_runner.py
- tests/unit/test_app_runners_batch6.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: positive controls for the structural stdout guard live here, matching the
    file's existing check_runner dispatch test convention
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'AFFECT001: _run_land_parity''s own affects()-closure doc needs the T-2486
    guard noted'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_planted_print_inside_json_run_does_not_corrupt_payload
- tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_legitimate_json_payload_is_byte_identical_with_guard_active
- tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_planted_print_still_reaches_stderr
- tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_no_planted_print_no_stderr_noise
- tests/unit/test_app_runners_batch6.py::TestJsonSubcommandEnumeration::test_more_than_one_subcommand_has_a_json_mode
designated_repro_test: null
acceptance:
- text: Given a print to stdout deliberately added inside a --json code path, when
    the command runs, then the JSON payload is not corrupted.
  evidence:
  - tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_planted_print_inside_json_run_does_not_corrupt_payload
- text: Given legitimate --json output, when the guard is in place, then the payload
    is byte-for-byte unchanged on both an idle and a busy machine.
  evidence:
  - tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_legitimate_json_payload_is_byte_identical_with_guard_active
  - tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_no_planted_print_no_stderr_noise
- text: Given a human-facing diagnostic emitted during a --json run, when the guard
    redirects it, then it still reaches the operator on stderr rather than being silently
    swallowed.
  evidence:
  - tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_planted_print_still_reaches_stderr
- text: Given every subcommand offering a --json mode, when the audit is complete,
    then the set is enumerated and each is reported as protected or not.
  evidence:
  - tests/unit/test_app_runners_batch6.py::TestJsonSubcommandEnumeration::test_more_than_one_subcommand_has_a_json_mode
threat: null
component: process
anchor: false
anchor_reason: null
land_commit: 040c99eb76d045dd46c52958e7fdf04ce8b003c2
---
T-2484 fixed one human-readable line leaking to STDOUT under
`frob check --json`. That fix is correct and landed. This ticket is
about the CLASS, not the instance.

WHY THE CLASS IS WORTH FIXING. The T-2484 leak was introduced minutes
after T-2473 landed, by an author who had no reason to know stdout was a
protected data channel under `--json`. It then:
  - broke `scripts/check_summary.py`, the repo's own recommended
    floor-measurement tool and the one the `frob-suggest` hook actively
    steers people toward;
  - was hit independently by a second agent, who WORKED AROUND IT by
    stripping the prefix and characterised it as a "gotcha" rather than
    a bug -- the workaround that, had it spread, would have made the
    corruption permanent and pushed responsibility onto every downstream
    parser;
  - reached the land path's `_parse_check_json`, which returns `None` on
    a decode failure and describes itself as "the sole gate between
    'trust this as a structured CheckResult' and 'fall back to
    nothing'".

That last one turned out fine -- T-2484 audited all four callers and
found none conflating unmeasured with no-findings -- but the margin was
luck, not design. The next leak may land somewhere less carefully
handled.

The defect is that the convention "stdout is data when `--json` is set"
is enforced only by every future author remembering it. T-2484's own
author audited every `print()` in `src/frob/__main__.py` and found the
rest already correct, but explicitly scoped OUT a repo-wide structural
guard (it would touch `check_runner.py` and beyond) and recorded it as a
candidate follow-up rather than filing. This is that follow-up.

Note the failure mode is load-dependent and therefore near-invisible in
testing: the advisory only printed when another check was already
running, so `--json` was clean on an idle machine and corrupt exactly
when the repo was busy. Any future leak gated on a similar condition
will behave the same way.

FIX SHAPE:
  - A structural guard at the output boundary: when `--json` is set,
    non-JSON writes to stdout are prevented or redirected to stderr,
    rather than each call site being individually correct. The
    mechanism matters less than the property -- a new `print()` written
    next month by someone who has never read this ticket must not be
    able to corrupt the payload.
  - Audit `check_runner.py` and the other command runners for existing
    instances while you are there, and report what you find even if the
    answer is zero.
  - Consider whether this generalises past `frob check` -- any
    subcommand with a `--json` mode has the same contract. Enumerate
    which ones have it; do not assume `check` is the only one.

DO NOT fix this by teaching consumers to strip prefixes or hunt for the
first `{`. That blesses the corruption. T-2484 makes the same point and
it is worth restating here because it is the tempting shortcut.

POSITIVE CONTROLS:
  - must-now-protect: a deliberately-added `print()` to stdout in a
    `--json` code path does not corrupt the payload -- plant one as the
    fixture, since that is precisely what happened.
  - must-still-emit: legitimate JSON output is unchanged, byte for
    byte, on both idle and busy machines.
  - must-still-inform: human-facing diagnostics still reach the
    operator on stderr; the guard must not silently swallow them, which
    would trade a parsing bug for an information-loss bug.