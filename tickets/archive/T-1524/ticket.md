---
id: T-1524
title: T-1514 pre-commit sweep false-positives on land-owned files the land itself
  stages (PRE001/SCOPE001 on .frob-release.json)
state: done
kind: bug
origin: human
created: '2026-08-04'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: the pre-commit sweep exemption fix lives here
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: exemption + nested-boundary unit tests
  actor: logan
  at: '2026-08-04'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_land_owned_only_findings_are_exempt_and_pass
- tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_nested_land_owned_name_is_not_exempt
- tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_checkpoint_artifact_rules_are_exempt
designated_repro_test: null
acceptance:
- text: GIVEN a land whose staged squash contains only land-machinery changes to land-owned
    files (.frob-release.json/CHANGELOG.md/pyproject.toml/uv.lock REL001 bump) beyond
    the ticket's own clean diff WHEN the T-1514 pre-commit unscoped sweep runs THEN
    findings against those root-level land-owned files are excluded (loudly logged)
    from the refusal decision and the land proceeds, while a nested same-named file
    still refuses
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_land_owned_only_findings_are_exempt_and_pass
  - tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_nested_land_owned_name_is_not_exempt
  - tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_checkpoint_artifact_rules_are_exempt
threat: null
component: null
---
The pre-commit unscoped sweep (_pre_commit_unscoped_error_sweep) compares fresh findings on the STAGED squash tree against the pre-land baseline with no exclusion for land-owned artifacts the land machinery itself writes at this checkpoint (.frob-release.json REL001 bump, CHANGELOG.md entry, pyproject.toml version, uv.lock resync). A land that needs a version bump stages a modified .frob-release.json, PRE001/SCOPE001 fire against it as new-vs-baseline, and the land is refused -- observed blocking T-1517 twice on 2026-08-04 while non-bumping lands (T-1515/T-1495) passed. Fix: exclude findings whose file is in the land-owned set from the pre-commit comparison, logging the exclusions (no silent caps); the post-land sweep and land's own REL001/ledger finalization already govern those files.