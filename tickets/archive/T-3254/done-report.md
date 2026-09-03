## Done report

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

### Changed
```
 docs/guides/release.md             | 155 ++++++++++++++++++++++++++++++++++---
 tickets/T-3254/ticket.md           |  99 ++++++++++++++++++++++-
 tickets/T-3337/ticket.md |  37 +++++++++
 3 files changed, 281 insertions(+), 10 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 8 error(s), None warning(s), None waived
- error-findings: CYCLE001@src/frob/__init__.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
