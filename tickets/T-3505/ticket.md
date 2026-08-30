---
id: T-3505
title: 'Windows works: drain T-3076''s failure set and remove the T-3425 advisory
  flag'
state: queued
kind: feature
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: epic
sprint: null
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- docs/design/windows-portability.md
- docs/guides/release.md
scope_breadth_ack: true
scope_breadth_ack_reason: epic tracking ticket, per-primitive scope lives on child
  leaves
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
EPIC: drain T-3076's measured 278 Windows-only test failures and remove
the T-3425 advisory continue-on-error flag from the windows-latest CI
leg, so 1.0.0 ships with a real (non-advisory) Windows CI gate.

MEASURED BASELINE (T-3076, GHA run 33035660969): 278 windows-only
failures, 54 traced to five missing POSIX primitives:
  22 fcntl (ModuleNotFoundError)
  12 os.sysconf (AttributeError)
  10 socket.AF_UNIX (AttributeError)
   8 multiprocessing fork context (ValueError: cannot find context)
   2 charmap UnicodeEncodeError
Remaining large buckets (33 assert False, 16 assert None-is-not-None,
11 SystemExit:1, ...) are expected -- per T-3076 -- to collapse once the
five primitives are fixed; they are NOT separately ticketed here and
must be re-measured, not guessed at.

WHY THIS BLOCKS 1.0.0: per owner decision, no release ships until the
windows-latest leg in .github/workflows/ci.yml is green (no
continue-on-error) and T-3425's advisory carve-out is removed.

SCOPE OF THIS EPIC: tracking/decision record only, per T-2963's own
stated posture for epics in this repo. All real work happens in child
tickets, one per primitive plus a re-measure leaf plus the flag-removal
leaf. Do not do primitive-fix work directly on this ticket.

CHILDREN (filed alongside this epic):
- T-3076 (characterization, already filed) -- linked as parent under
  this epic, not re-scoped.
- T-2963 (Windows-native daemon transport epic, already filed) -- the
  AF_UNIX primitive child below is a scoped SLICE of T-2963 (loud
  refusal + parity, not the full transport epic); T-2963 itself stays
  linked as a related epic for the eventual real-transport follow-on,
  which is explicitly OUT of 1.0.0 scope per T-2963's own body.
- five primitive leaves (fcntl portable lock, os.sysconf fallback,
  AF_UNIX loud-refusal parity, fork->spawn context, charmap->utf-8 io)
- one re-measure leaf, blocked by all five
- one flag-removal leaf, blocked by the re-measure leaf

ACCEPTANCE
- T-3076's own acceptance criteria are met (each primitive has a real
  implementation or a loud, declared, non-silent unsupported boundary;
  file locking is correct or refuses, never silently no-ops; the
  degradation-direction test failures are fixed as their own change;
  a completed, not-interrupted Windows run with a stable count).
- continue-on-error is removed from .github/workflows/ci.yml's
  windows-latest leg.
- tests/unit/test_release_workflow_gate.py and docs/guides/release.md's
  "what green means" note are updated to match.
- docs/design/windows-portability.md (T-3425) is updated to record the
  boundary's closure, not deleted (it stays as the historical record of
  why the flag existed).
