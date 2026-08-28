---
id: T-3254
title: 'frob release check REFUSES 0.530.0 (BUMP REQUIRED, need >= 0.531.0): no documented
  release-cut procedure places the version bump'
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/release.md
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
MEASURED 2026-08-28. The repo's own release gate REFUSES the version the owner
was told it would publish:

    $ uv run frob release check
    since 0.530.0: major change -> need >= 0.531.0 (current 0.530.0): BUMP REQUIRED
    REAL_EXIT=1

So `0.530.0` is NOT publishable as-is. The public API has moved past the point
`.frob-release.json` was stamped, and REL001 correctly demands >= 0.531.0.
`CHANGELOG.md` already carries a `[0.531.0] - unreleased` heading, so two of the
repo's three version-bearing artifacts already disagree with pyproject's
`version = "0.530.0"`.

THE OWNER'S DECISION IS NOT INVALIDATED, ONLY ITS NUMBER. The decision (recorded
in T-3251/T-3190) was to publish at the repo's MECHANICAL authority rather than
renumber to a cosmetic pre-1.0 number. That still holds. The mechanical
authority simply says 0.531.0 or higher, not 0.530.0. The owner must be told the
number moved; do not silently substitute it.

THE SEQUENCING FACT THAT MATTERS MOST. REL001 compares the live public-API graph
against the stamped digest, so EVERY land that changes the public API
re-invalidates the stamp. Bumping the version now does not stick -- it will be
stale again within a few lands. The version bump is therefore the LAST step
before a release cut, not preparation work that can be done in advance. Any plan
that bumps early and then keeps landing produces a published version whose own
gate fails.

WHAT IS MISSING. `docs/guides/release.md`'s "Sequencing: build now, first publish
gated on green + consent" section lists exactly two preconditions -- a green
matrix and recorded owner approval -- and says nothing about the version bump at
all. `frob release stamp` and `frob release sync` exist (sync regenerates
pyproject's version, uv.lock and the CHANGELOG skeleton from
`.frob-release.json`, REL002) but no documented procedure says WHEN to run them
relative to the freeze, the tag, and the dispatch.

There is also no git tag in this repository. `git tag` returns nothing; there has
never been a tagged release. Whether the cut creates one, and at what point, is
undefined.

WHAT TO BUILD -- a written, ordered release-cut procedure, and mechanical checks
for the parts that can be checked:
  1. The ordered steps from "main is green" to "wheels uploaded", naming the
     exact commands. At minimum it must place: freeze, `frob release stamp`,
     `frob release sync`, the VERSION001 coupling re-check across all three
     packages, the tag, the dispatch, and the owner's environment approval.
  2. A check that the three version-bearing artifacts agree at cut time
     (pyproject `version`, `.frob-release.json`, the CHANGELOG's top heading)
     and that `frob release check` exits 0. Today they disagree and nothing
     fails.
  3. State whether a git tag is created, and if so at which step and by whom.
     Do not create a tagging automation that could trigger a publish -- T-3011
     deliberately left no tag trigger in release.yml and that must stay true
     (tests/unit/test_release_workflow_gate.py asserts it).

ALSO IN SCOPE, SAME FILE: the sequencing section's failure numbers are stale. It
says "Windows ~19 test failures across 7 files, macOS ~144 uncharacterised
failures, Linux never producing a verified green full-suite baseline". Linux now
HAS an authoritative baseline (T-2992's Done report, 12,035/12,039, 86 failures
mapped to seven clusters, six of them since closed). Refresh those numbers or
replace them with a pointer to the live source, so the guide does not keep
asserting a state that measurement has moved past.

DO NOT bump the version under this ticket. Bumping now is precisely the mistake
this ticket documents. Write the procedure and the checks; the bump happens at
the real cut.

ACCEPTANCE
- A documented, ordered release-cut procedure naming exact commands.
- A mechanical check that the version-bearing artifacts agree and `frob release
  check` is clean, with a must-fire fixture (they disagree -> refused) and a
  must-stay-quiet fixture (they agree -> silent).
- The stale failure numbers in docs/guides/release.md corrected.
- No version bumped, no tag created, no release dispatched under this ticket.
- No T-3011 consent gate weakened; say explicitly that you checked.
