---
id: T-4086
title: dependabot proposes a 3-major jump on upload-artifact, used only in release.yml
  which no routine CI run exercises
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/release.yml
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
DEPENDABOT HAS PROPOSED A MAJOR-VERSION JUMP ON A RELEASE-CRITICAL ACTION, AND IT
TOUCHES ONLY THE WORKFLOW THAT CI DOES NOT EXERCISE.

Observed 2026-09-06: dependabot opened `chore(deps): bump actions/upload-artifact
from 4.6.2 to 7.0.1`. That is the update path T-3922 deliberately created -- every
third-party `uses:` is pinned to a 40-hex SHA, and .github/dependabot.yml is the
sanctioned way to move a pin. The mechanism is working as designed. THE RISK IS
WHERE IT LANDS.

`actions/upload-artifact` appears FIVE TIMES, ALL IN .github/workflows/release.yml
(lines 129, 135, 163, 168, 173) -- and NONE in ci.yml. release.yml is
`workflow_dispatch:` ONLY (T-3011), so it does not run on push. THEREFORE:

    MERGING THIS BUMP CHANGES A WORKFLOW THAT NO ROUTINE CI RUN EXERCISES.

A green CI run on the dependabot PR proves nothing about it. The first execution
of the new version would be the release we cut -- which is the single run where a
failure is most expensive and least recoverable.

THIS IS ALSO A KNOWN-BREAKING JUMP. actions/upload-artifact v4 was itself a
breaking change (artifact immutability, no same-name re-upload, changed download
behaviour); v5-v7 have continued to move. A 4.x -> 7.x jump across three majors on
five call sites, including the ones that carry the built wheels and the core
wheels, is not a routine pin refresh.

WHAT TO DO, AND THE ORDER MATTERS:
1. DO NOT MERGE ON A GREEN CI SIGNAL. State explicitly on the PR that ci.yml does
   not exercise this action, so its green tells us nothing.
2. EXERCISE release.yml DELIBERATELY before merging -- it is workflow_dispatch,
   so it can be run on demand. That is the only real test.
3. READ THE UPGRADE NOTES for v5, v6 and v7 and check each of the five call sites
   against them, particularly the artifact-name/overwrite semantics the smoke and
   core-wheel jobs depend on (T-3935 wired --find-links over those artifacts;
   T-3884 added the artifact-smoke job that consumes them).
4. CONSIDER PINNING dependabot TO MINOR/PATCH for release-critical actions, or
   requiring a dispatch run before a major bump is merged. The current config
   proposes majors for a workflow nothing routinely runs, which is the worst
   combination.

THE GENERAL POINT WORTH RECORDING: A DEPENDENCY UPDATE PATH IS ONLY AS SAFE AS
THE TEST COVERAGE OF WHAT IT UPDATES. T-3922 correctly made pins updatable; it did
not (and could not) make release.yml exercised. So we have automated proposals
landing in the least-tested workflow in the repo. That gap belongs on the alpha
checklist, because a broken release.yml is discovered at exactly the wrong moment.

MUST-FIRE FIXTURE: a release.yml dispatch run succeeds end to end with the bumped
action, producing and consuming the same artifacts.
MUST-STAY-QUIET: the pinned-SHA discipline is unchanged -- no hand-unpinning to
make it work.

ACCEPTANCE
- The bump exercised via a workflow_dispatch release run, not merged on CI green.
- All five call sites checked against the v5/v6/v7 upgrade notes.
- A decision recorded on whether dependabot should propose majors for
  dispatch-only workflows.