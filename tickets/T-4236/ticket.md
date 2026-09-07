---
id: T-4236
title: 'make the Windows CI leg green and remove its advisory flag: the owner will
  not cut a PyPI release until it passes'
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: critical
parent: null
tier: epic
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
acceptance:
- text: given the Windows CI leg on current main, when a complete run finishes, then
    it reports zero failures
  evidence: []
- text: given the workflow definition, when Windows passes, then its continue-on-error
    flag is removed and the job gates the run conclusion
  evidence: []
- text: given the path-shape failures, when they are fixed, then the fix is one shared
    mechanism rather than a per-test correction
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MAKE THE WINDOWS LEG GREEN AND REMOVE ITS ADVISORY FLAG. Owner decision: no PyPI
release until Windows passes, not merely until it is allowed to fail.

THIS EPIC EXISTS BECAUSE THE ADVISORY FLAG HAS A WRITTEN REMOVAL CONDITION AND WE
ARE NOW COMMITTING TO MEETING IT. The workflow declares the Windows job
continue-on-error under T-3425, with a comment saying to remove the flag when the
failure set reaches zero. That is the finish line. Removing the flag is part of
this epic, not a follow-up.

THE CURRENT SET, taken from the last COMPLETE Windows run (25 failures). Four
groups, and the first two are already resolved or filed, so the genuinely open
work is smaller than 25:

ALREADY FIXED ON MAIN, EXPECT THEM GONE -- CONFIRM BEFORE ASSUMING (7):
  the four flag-coverage gate tests, two ruff-argv tests in the check suite, and
  the coverage worker-count test. All seven were the no-sync spawn-kind defect
  landed as T-4171. They are platform-independent and were never Windows
  findings; they inflated this count and must be subtracted before any tally.

ALREADY FILED, NOT YET FIXED (3):
  the two path-shape mechanism fixtures -- T-4155, where a measured comparison
  shows the pathspec migration left separator handling platform-dependent;
  the scaffold end-to-end console-script test -- T-4234, our own regression from
  today, which hardcodes the posix virtualenv script directory.

THE DOMINANT REMAINING CLASS IS PATH SHAPE, AND IT IS ONE MECHANISM SEEN FOUR
TIMES: a Windows path rendered with backslashes compared against a forward-slash
string that came from git, from a symref, or from a log line.
  land-core: a ticket path stringified from a path object is checked for
    membership in git's own output, which uses forward slashes
  arch symref canonicalisation: a violation's symref and a waiver's source differ
    only in separator
  rapid sweep: an absolute path is checked for membership in a log message
  lang primitives: a symbol span comparison that also differs by a trailing
    newline, so this one is line endings as well as separators
FIX THESE AS ONE MECHANISM, not four tests. The producers should emit POSIX and
the comparisons should be against POSIX; this repository already has a shared
conversion helper introduced for exactly this reason and several producers
already routed through it.

THE REMAINDER ARE INDIVIDUALLY DISTINCT AND NEED SEPARATE DIAGNOSIS (8):
  a TTY-detection assertion in the attach CLI
  the gate cache serving a stale hit after a tracked-file edit
  pre-land lint diff attribution refusing a line-shift-only change
  two tests asserting a clean tree that find an untracked lock file left behind
  the evidence command's shell-metacharacter safety check failing outright
  the agent-env stdout purity check, whose captured output is UTF-16 encoded --
    that is an encoding defect, not a path one, and it is the only one of its kind
  the land-lock reclaim path logging nothing where the test expects a reclaim line
  a native-call timeout watchdog not firing
  an out-of-tree release bump returning a different commit than composed
Several of these are plausibly real defects that only Windows exposes, rather
than test artifacts. Do not assume test-only; diagnose each.

SEQUENCING, AND THE FIRST STEP IS MEASUREMENT NOT FIXING:
  1. Get one COMPLETE Windows run on current main. The most recent attempt
     aborted with an internal scheduler error, reported its failing set as
     incomplete, and had a worker die at five minutes under suspected memory
     pressure -- so the current true count is unknown. Everything below depends on
     a real denominator.
  2. Subtract the seven now-fixed. Confirm rather than assume.
  3. Fix the path-shape class as one change.
  4. Diagnose the remainder individually, filing a leaf each where the cause is
     not obvious.
  5. Remove the advisory flag and prove the leg gates the run.

TWO STANDING CAUTIONS FOR EVERY LEAF HERE, both learned the hard way today:
  A fixture that asserts platform behaviour must RUN on that platform. Three
  times this drive a Windows claim was reasoned out on linux and was wrong --
  including a replacement fixture written to fix the first instance.
  The abort shape matters. A run that ends with an internal error is UNMEASURED,
  not a partial result, and its count must never be compared against a complete
  run's.

ACCEPTANCE
- One complete Windows run recorded on current main, with its true failing set.
- The path-shape class fixed as a single mechanism, not per test.
- Every remaining failure either fixed or filed with a diagnosis.
- The advisory flag removed and the Windows job gating the workflow conclusion.
