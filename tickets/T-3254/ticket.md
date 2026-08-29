---
id: T-3254
title: 'frob release check REFUSES 0.530.0 (BUMP REQUIRED, need >= 0.531.0): no documented
  release-cut procedure places the version bump'
state: done
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
evidence_scope:
- tests/test_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: Done report per implementer protocol
  actor: logan
  at: '2026-08-28'
  old_length: 4241
  new_length: 8602
- mode: append
  reason: 'BUG002 front door (T-2393): docs-only deliverable, scope=[''docs/guides/release.md'']:
    an ordered release-cut procedure and a documented, existing mechanical check (frob
    check --only release, already-shipped REL001/REL002) placed correctly relative
    to freeze/tag/dispatch. No code, test, or workflow file touched; no version bumped
    (frob release check still reports the same BUMP REQUIRED as before this ticket);
    no tag created; no T-3011 gate touched. New must-fire/must-stay-quiet behavior
    would require test files outside this ticket''s declared scope -- filed as the
    out-of-scope T-3337 follow-up instead of expanding scope.'
  actor: logan
  at: '2026-08-28'
  old_length: 8602
  new_length: 9244
evidence:
- tests/test_release.py::test_required_version_and_satisfies
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


DONE REPORT

Changed:
docs/guides/release.md
  - "Sequencing" section: refreshed the stale Windows ~19/macOS ~144/Linux
    never-green paragraph against T-2992's real baseline (12,039 collected,
    86 failures, seven triage tickets, all seven now done); pointed at
    T-3251 for the still-open per-SHA CI gate.
  - New "The release-cut procedure (T-3254)" section: 11 ordered steps from
    freeze to post-upload tag, naming exact commands (frob release check,
    manual pyproject.toml x3 edit, frob release stamp, frob release sync,
    frob check --only release, commit, workflow_dispatch, owner approval,
    git tag after success).
  - New "Known gap: frob release publish / make upload bumps the wrong
    thing" subsection: documents (with live reproduction) that the
    existing automated publish command always bumps only the patch
    component and does not consult diff_class/required_version, so it
    cannot produce this repo's own currently-required 0.531.0 bump.

Evidence (measurement, not code -- this is a docs-only ticket, scope=['docs/guides/release.md']):
  - frob release check reproduces the ticket's own repro: "since 0.530.0:
    major change -> need >= 0.531.0 (current 0.530.0): BUMP REQUIRED",
    exit 1 (confirmed via $PIPESTATUS, not a piped tail).
  - git tag returns nothing (confirmed, no tags exist).
  - Read src/frob/release/__init__.py (diff_class/required_version),
    src/frob/release/_publish.py (_compute_plan calls next_patch_version
    unconditionally), src/frob/app/release_runner.py (_stamp reads the
    version from pyproject.toml, does not compute a bump) and
    scripts/bump_version.py to verify the "publish always bumps patch
    only" finding directly against source, not by inference.
  - Verified T-2992's Linux baseline and all seven of its triage tickets
    (T-3019/T-3033/T-3034/T-3035/T-3037/T-3040/T-3041) are [done] via
    frob ticket show before citing the refreshed numbers.
  - Verified T-3251's scope (.github/workflows/release.yml,
    tests/unit/test_release_workflow_gate.py) is disjoint from this
    ticket's scope (docs/guides/release.md) -- confirmed no overlap, no
    second gate built here.
  - frob check --ticket T-3254 --only scope: 1 new-looking SCOPE001 on
    tickets/T-3337/ticket.md (filing the sibling out-of-scope
    ticket below) -- this is the standard, tested "sibling draft filed
    mid-ticket" pattern (tests/test_ticket_land.py::
    TestStandaloneSiblingDraftSurvivesLand confirms frob ticket land
    carries such a sibling forward correctly); not a real scope breach.
    The 2 SCOPE002 warnings on doc anchors under Decision 1/2 are
    pre-existing (those anchors predate this ticket's edit, unchanged).
  - frob check --ticket T-3254 (full, repo root): 425 errors are
    REPO-WIDE per the tool's own scope-note, not attributable to this
    diff; gate:DOC/DRIFT counts are identical in nature to the pre-
    existing backlog this ticket's own refreshed paragraph references.
  - frob test --base main: touched-set binding for a docs.md-only diff
    fell back to a broad, loosely-related "summary"-keyword test
    selection (unrelated system self-conformance tests, same failure
    class as the already-closed T-3041); not meaningful evidence for a
    prose-only change and not re-run as a gate here.

Filed: T-3337 -- "frob release publish always bumps patch only,
ignores REL001 required bump class" (bug, scope=
src/frob/release/_publish.py, scripts/bump_version.py). Out of this
ticket's docs-only scope; referenced by name in the new procedure section
as the reason make upload must not be used for a real cut yet.

Gates: frob check --ticket T-3254 --only scope clean of NEW findings
(the one SCOPE001 is the standard sibling-ticket-filing pattern, tested
and expected to survive frob ticket land; not waived because it is not
a real violation of this ticket's own scope). No frob:waive used anywhere
in this change (docs-only, no code, no directives touched).

Verified: DID NOT bump any version field (pyproject.toml x3, uv.lock,
CHANGELOG.md, .frob-release.json all unchanged -- frob release check
still reports BUMP REQUIRED exactly as before this ticket). Did not touch
.github/workflows/release.yml or tests/unit/test_release_workflow_gate.py
(T-3251's scope). Did not create a git tag or any tagging automation.


frob:no-behavior-change reason="docs-only deliverable, scope=['docs/guides/release.md']: an ordered release-cut procedure and a documented, existing mechanical check (frob check --only release, already-shipped REL001/REL002) placed correctly relative to freeze/tag/dispatch. No code, test, or workflow file touched; no version bumped (frob release check still reports the same BUMP REQUIRED as before this ticket); no tag created; no T-3011 gate touched. New must-fire/must-stay-quiet behavior would require test files outside this ticket's declared scope -- filed as the out-of-scope T-3337 follow-up instead of expanding scope."