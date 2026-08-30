---
id: T-3512
title: Remove T-3425 windows-latest continue-on-error advisory flag
state: queued
kind: feature
origin: human
created: '2026-08-30'
priority: high
blocked_by:
- T-3511
parent: T-3505
tier: ticket
sprint: null
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/unit/test_release_workflow_gate.py
- docs/guides/release.md
- docs/design/windows-portability.md
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
Remove the T-3425 advisory continue-on-error flag from the
windows-latest leg of .github/workflows/ci.yml, update
tests/unit/test_release_workflow_gate.py and
docs/guides/release.md's "what green means" note to match, and record
the closure in docs/design/windows-portability.md.

WHY NOW, NOT BEFORE: per the owner's 1.0.0 decision, no release ships
until windows-latest is green AND this flag is gone. Doing this before
the re-measure leaf (T-3511) confirms zero would either fail CI
immediately (if failures remain) or, worse, mask a false green if the
re-measurement was skipped. This leaf is intentionally LAST and
blocked accordingly.

WORK
- Remove `continue-on-error: ${{ matrix.os == 'windows-latest' }}` (and
  its T-3425 explanatory comment block, lines ~19-30 of ci.yml as of
  bb5c28203) from the `build` job in .github/workflows/ci.yml.
- Update tests/unit/test_release_workflow_gate.py if it has (or gains)
  any assertion about the advisory flag's presence -- confirm via
  `git grep -n "continue-on-error\|T-3425" -- tests/unit/test_release_workflow_gate.py`
  first; if no such assertion exists today, consider adding a
  MUST-STAY-QUIET regression test asserting the flag is ABSENT, so a
  future edit can't silently reintroduce it without a ticket.
- Update docs/guides/release.md's "what green means" note (referenced
  from docs/design/windows-portability.md's "Removing the advisory
  flag" section) to say scripts/verify_release_ci_status.py reads
  GREEN off all three legs again, not just ubuntu/macos.
- Update docs/design/windows-portability.md itself: do not delete it;
  add a closure note recording when/how the flag was removed and
  linking the re-measured T-3511 baseline, per T-3425's own body
  ("That removal should land as an explicit acceptance line on T-3076
  itself, not edited into T-3076's body from this ticket" -- also true
  here: record the removal as an acceptance line on T-3076, and as a
  closure section on this doc, not a silent deletion of the boundary's
  history).
- Record the removal as a completed acceptance line on T-3076.

FILES IN SCOPE
  .github/workflows/ci.yml
  tests/unit/test_release_workflow_gate.py
  docs/guides/release.md
  docs/design/windows-portability.md

MUST-FIRE
- windows-latest is a normal, blocking matrix leg again: no
  continue-on-error anywhere in ci.yml's build job.
- test_release_workflow_gate.py passes and (ideally) now guards against
  reintroduction of the advisory flag.
- docs/guides/release.md and docs/design/windows-portability.md
  reflect the closure.

MUST-STAY-QUIET
- ubuntu-latest/macos-latest legs' configuration is untouched.
- release.yml's manual-dispatch-only trigger and upload-job consent
  gate (TestReleaseWorkflowNoAutomaticTrigger /
  TestUploadJobConsentGate in test_release_workflow_gate.py) are
  unaffected -- this leaf touches only the windows-latest advisory
  carve-out, nothing about release triggering or the PyPI gate.

BLOCKED BY: T-3511 (re-measure) -- this must be the truly last leaf;
removing the flag before a stable-zero re-measurement would either
immediately redden CI or, if the re-measurement step was skipped,
falsely certify a release gate that was never actually verified green.
