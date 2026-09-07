---
id: T-4268
title: 'take the five pending github action updates in a deliberate order after the
  alpha publish: they clear a runtime deprecation but collide with three workflow
  rewrites in flight'
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- .github/workflows/release.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the runtime deprecation annotation on every integration job, when the
    three responsible action updates are merged, then a complete run emits no such
    annotation
  evidence: []
- text: given the five updates, when they are merged, then each lands in its own run
    rather than as a batch, so a red result names one cause
  evidence: []
- text: given the two updates that touch only the release workflow, when they are
    merged, then the upload job split has already landed and the alpha has already
    published
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TAKE THE FIVE PENDING GITHUB ACTION UPDATES, IN A DELIBERATE ORDER, AFTER THE
ALPHA PUBLISH. Five automated dependency pull requests are open against the two
workflows. This ticket records what they are, why they are not being merged
immediately, and what must be true before each one is.

THEY FIX A REAL DEPRECATION, NOT JUST A VERSION NUMBER. The integration run
currently emits a deprecation annotation on every job: three actions target a
runtime that the runner no longer supports and are being forced onto a newer one.
Those three actions are the checkout action, the cache action, and the uv setup
action, and three of the five pull requests are exactly those. A forced runtime
is a warning today and a breakage on whatever date the forcing stops, so this is
scheduled maintenance with a deadline someone else sets, not optional polish.

WHAT EACH ONE TOUCHES, MEASURED RATHER THAN ASSUMED. Two of them change both
workflows. One changes only the integration workflow. Two change only the release
workflow. An earlier reading of mine said two were integration-only; that was
wrong, and the release workflow is in scope for four of the five. Verify each
pull request's own file list before merging it rather than trusting this
paragraph.

WHY THEY WAIT. Every one of them edits a file that at least one open ticket is
also rewriting: the upload job is being split per distribution so each new index
project can register its own publisher, the two kernel crates are moving to a new
directory which changes several working directories and artifact paths, and the
obsolete diagnostic scaffolding is being deleted from the integration workflow.
Merging a dependency bump into a file mid-rewrite produces conflicts that a
person has to resolve by hand in exactly the code path a release depends on.

THE VERSION JUMPS ARE LARGE. These are not patch bumps; several cross multiple
major versions, which means the pinned references are old enough that behaviour
may genuinely differ. Read each action's own release notes for breaking changes
before merging, particularly for the artifact actions, whose upload and download
semantics have changed across majors in ways that silently alter what a later
step finds.

THE ORDER TO WORK IN.
  First, publish the alpha. Nothing here should touch the release path while an
  imminent publish depends on it.
  Then take the integration-workflow-only update, which is the smallest and
  cannot affect the release path at all.
  Then the two that span both workflows, one at a time, letting a complete run
  finish between them so a failure has one obvious cause.
  Last, the two that touch only the release workflow, and only once the upload
  job split has landed, since that ticket rewrites the same steps.

DO NOT MERGE THESE AS A BATCH. Five simultaneous bumps to workflow
infrastructure, several crossing majors, share one failure signal. If the run
goes red, you will not know which one did it, and the cheapest recovery is
reverting all five, which wastes the whole exercise.
