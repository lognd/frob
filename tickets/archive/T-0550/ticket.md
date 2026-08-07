---
id: T-0550
title: 'gates: COV002/SCOPE001/bare-TODO fail open on empty/failed diff (B8)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0403
tier: ticket
sprint: null
scope:
- src/frob/gates/
- pyproject.toml
- .frob-release.json
- frob.lock
- uv.lock
- CHANGELOG.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: REL001 version bump for coverage_gate's new diff_load_failed param (public
    API change)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 version bump for coverage_gate's new diff_load_failed param (public
    API change)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: frob.lock
  reason: REL001 version bump for coverage_gate's new diff_load_failed param (public
    API change)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 version bump for coverage_gate's new diff_load_failed param (public
    API change)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 needs a CHANGELOG entry for the version bump(s) this ticket's release
    stamp covers
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestGatesDegradeWithoutDiff::test_diff_dependent_gates_block_loudly_on_failed_diff
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B8. _load_diff degrades to an EMPTY diff (warning only) when working_diff fails; COV002/SCOPE001/bare-TODO are all diff-driven so an empty diff makes them all silently pass. Default base is main, so committing directly on main or with a bad --base zeros the touched set. Fix direction: a failed working_diff should be a loud blocking condition for these gates, not a silent empty-diff degrade.