---
id: T-3075
title: Five tests read ambient developer state (global git identity, real ~/.claude)
  and so pass locally but fail in CI
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_land_duplicate_ticket_id.py
- tests/system/test_cli_ticket.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Record the measured CI-only failures, the two candidate fixes, and why hermeticity
    is preferred over supplying ambient state in the workflow
  actor: logan
  at: '2026-08-26'
  old_length: 0
  new_length: 4027
- mode: append
  reason: 'document the environment-dependent-defect BUG002/TEST016 escape hatch:
    the repro only fails absent ambient git identity, which this sandbox''s close-time
    verification does not simulate

    '
  actor: logan
  at: '2026-08-27'
  old_length: 4026
  new_length: 5691
evidence:
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_the_landing_tickets_own_id
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_an_id_that_already_existed_at_the_merge_base
designated_repro_test: tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: fb81130b34373a5fd805c2d5084840ba07ca6d65
---
MEASURED on GitHub Actions run 33035660969 (ubuntu-latest, job 98397679801),
the first CI run in which all three platforms reached the Test step. 93 tests
failed. Five of them fail for a reason that has nothing to do with the code
under test: the test reads AMBIENT DEVELOPER STATE that exists on the author's
machine and does not exist on a runner.

CLASS A -- git identity (3 tests)

    tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides
    tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_the_landing_tickets_own_id
    tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_an_id_that_already_existed_at_the_merge_base

Each builds a throwaway repo under `/tmp/pytest-of-runner/...` and runs
`git commit` in it, relying on a globally configured `user.email`/`user.name`.
The runner has none, so git refuses with "Author identity unknown ... tell me
who you are" and the test dies as `subprocess.CalledProcessError`. Confirmed by
grep: `Author identity unknown` appears 3 times in the job log, and
`.github/workflows/ci.yml` configures no git identity anywhere.

CLASS B -- the author's real ~/.claude (2 tests)

    tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_start_auto_plans_queued_ticket
    tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_plan_then_sweep_flow

Both fail with `AssertionError: Claude config DRIFT: 9 managed file(s) differ
from ~/.claude, 0 source(s)`. A ticket round-trip test is asserting against the
developer's real home directory. On a runner that directory is empty or absent,
so every managed file reads as drifted.

WHY THIS IS WORTH ITS OWN TICKET RATHER THAN FIVE FIXES: these tests PASS
LOCALLY AND FAIL IN CI, which is the exact signature of a test that is
measuring the machine instead of the code. That makes them worse than an
ordinary failure -- they are green on the developer's box, so they provide
false assurance, and they are indistinguishable in a CI summary from a real
regression. This repo has a recorded doctrine that a gate must not silently
depend on the environment it happens to run in (PLATFORM001: declare the
boundary, never degrade silently); ambient-state dependence is the test-side
instance of the same rule.

TWO FIXES ARE POSSIBLE AND THEY ARE NOT EQUIVALENT -- CHOOSE DELIBERATELY:

  (i) Make CI supply the ambient state (add `git config --global user.email`
      to the workflow). This makes the symptom go away and leaves the
      hermeticity defect in place; the next such test will fail the same way.
  (ii) Make the tests hermetic -- set identity per-repo in the fixture
      (`git -c user.email=... commit`, or `git config` in the temp repo), and
      point the Claude-config check at a temp HOME rather than the real one.

Prefer (ii). (i) may ALSO be worth doing as defence in depth, but it must not
be the only change, and if you do only (i) say so explicitly and explain why.

ALSO IN SCOPE -- find the rest before they bite. These five surfaced only
because CI finally reached the Test step for the first time. Sweep for the
same class rather than fixing only the observed instances: tests that read
`~`/`$HOME`, invoke `git` without a per-invocation identity, or read global
git config. Report the count found, including any that currently pass by luck.

ACCEPTANCE
- All five named tests pass on a runner with no global git identity and no
  populated `~/.claude`.
- The fix is hermeticity-side (ii), or if the workflow was also changed, the
  reason is stated.
- A sweep for the same ambient-state class is reported with a count, and each
  additional instance is either fixed or filed.
- Must-stay-quiet check: the tests still pass on a normal developer machine
  that DOES have git identity and a populated ~/.claude -- a hermetic test must
  be insensitive to that state in both directions, not merely tolerant of its
  absence.

frob:waive BUG002 reason="the defect (git clone dropping the source repo's local, non-global config, so a commit inside the clone silently relies on ambient GLOBAL git identity) is only reproducible in an environment with NO ambient git identity at all -- confirmed directly by running the designated repro under HOME pointed at an empty throwaway directory with GIT_CONFIG_GLOBAL/GIT_CONFIG_SYSTEM=/dev/null (frob ticket evidence --check-repro genuinely reports FAILED_AT_PARENT under those conditions). This repo's own dev/CI verification environment carries a real global git identity, so the automatic close-time BUG002 re-check (which does not reapply that environment override) correctly reports the repro PASSING at parent under ITS OWN ambient identity -- the same 'passes locally, fails in CI' asymmetry this ticket exists to fix, now visible in the verification tooling itself rather than only in the original failure. This is the T-2076/BUG002 environment-the-suite-cannot-create case its own escape hatch names."

frob:waive TEST016 reason="same root cause as the BUG002 waiver above: mutation testing runs in this sandbox's own ambient-identity environment, where the pre-fix code already passes (the mutation cannot be distinguished from a no-op without the CI-like no-identity condition the standard mutation harness does not simulate). Verified the real fix behavior manually in both directions instead: FAILED_AT_PARENT confirmed under a simulated no-identity HOME, and PASSED post-fix under that same simulated environment, plus PASSED under this sandbox's real ambient identity (must-stay-quiet) -- see the Done report for the exact commands."