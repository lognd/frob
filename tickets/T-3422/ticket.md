---
id: T-3422
title: 'cross-worktree lease-pin refusal lost its remediation text: refuses correctly
  but no longer names frob ticket start'
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
The cross-worktree lease-pin refusal still REFUSES correctly but no longer
tells the user how to resolve it. The remediation instruction was dropped from
the message while the enforcement stayed intact.

MEASURED 2026-08-29, serial run of tests/system on an idle box, no coverage
instrumentation, real node id:

    tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal
        ::test_ticket_lease_recorded_elsewhere_refuses

    tests/system/test_cli_check.py:1084: AssertionError
    assert "frob ticket start" in out
    E   AssertionError: assert 'frob ticket start' in
        'frob check /tmp/.../wt  [FAIL]  1 error  0 warnings\n\n## Err...
         it did NOT do the work you may think it did -- a fast failure is not
         a fast success.\n'

WHAT STILL WORKS. The three assertions before the failing one all pass:

    assert r.returncode == 1        exits 1, does not silently succeed
    assert out.strip()              the refusal is not silent
    assert ticket_id in out         it names the ticket

So the guard is doing its job. Scenario: `frob check --ticket <id>` run from a
SECOND linked worktree when that ticket's lease is recorded against the FIRST
(main) worktree. It refuses, loudly, naming the ticket.

WHAT BROKE. The message no longer contains `frob ticket start`, which is the
one string telling the operator what to actually do about it. The test's own
docstring states the contract: exits 1 "with a refusal naming `frob ticket
start <id>` -- never a silent pass and never a crash".

WHY THIS IS WORTH FIXING RATHER THAN RETARGETING THE TEST. The obvious cheap
move -- relax the assertion to match whatever the message says now -- would be
wrong. A refusal that does not say how to proceed is a dead end for whoever
hits it, and this particular refusal fires in the exact situation where the
operator is least likely to know the answer: they are in a worktree, the lease
lives somewhere else, and nothing on screen names the verb that fixes it. The
repo already treats unhelpful-but-correct refusals as defects.

FIRST TASK IS ATTRIBUTION, NOT REPAIR. Find the commit that dropped the string.
Several lands touched refusal-message construction today (T-3397 extracted a
refusal tail into `_refuse_pre_land_lint`; T-3394 extracted one into
`_refuse_unscoped_fix_pass`; T-3404 changed argparse option handling). Any of
those, or none, could be responsible -- do not guess. `git log -S "frob ticket
start"` over the relevant sources will name it directly. Report the commit and
the ticket that landed it.

CAUTION ON THE SEARCH: this string appears in many places for unrelated
reasons. Narrow to the code path this test exercises (the lease-pin refusal in
the check runner), not every occurrence in the tree.

WATCH FOR THE SAME LOSS ELSEWHERE. If a refactor dropped remediation text from
one refusal, check whether it dropped it from siblings built the same way.
Enumerate the refusal messages in that code path and report which ones still
carry an actionable next step. That enumeration is the valuable half of this
ticket; a one-line string restoration is the cheap half.

MUST-FIRE FIXTURE:   the existing test passes -- the refusal names
                     `frob ticket start`.
MUST-STAY-QUIET:     a legitimately-leased `frob check --ticket` from the
                     owning worktree still succeeds and is not refused.

ACCEPTANCE
- The dropping commit named, or a statement with evidence that the string was
  never present and the test asserted an unimplemented contract.
- Sibling refusal messages in the same path enumerated, with a verdict on each.
- Both fixtures present. Do not weaken the assertion to match current output.

## Failure log
- 2026-08-29 attempt 1: already fixed by T-3028 (landed): the described failure was a project-type MISDETECTION bug (a src/-layout Python repo with no root marker resolved to 'unknown', so CHECK001 fired before the lease-pin check ever ran), not a dropped remediation string -- git log -S 'run: frob ticket start %s' -- src/frob/app/check_runner.py shows exactly ONE commit (db7948d57, T-0787) ever introduced that string and it has never been removed since; _refuse_ticket_lease_mismatch still runs before project-type dispatch in check_runner.run() and still emits the frob-ticket-start remediation text. Re-ran tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses 3x on a worktree built off current main (post T-3416/T-3409/T-3429): PASSED every time. No code change made; scope was never touched.
