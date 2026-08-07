---
id: T-0992
title: 'land REL001 bump keys on the worktree''s carried version, regressing main''s
  (two incidents: T-0976, T-0989)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 requires updating the affects()-closure doc for _apply_release_bump
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_ticket_land.py::TestReleaseBump::test_stale_worktree_version_bump_yields_main_plus_one
- tests/test_ticket_land.py::TestReleaseBump::test_downgrade_bump_is_refused
designated_repro_test: null
acceptance:
- text: given a worktree whose pyproject carries an older version than main, when
    its ticket lands with a REL001 bump, then the resulting version is strictly greater
    than main's pre-land version
  evidence:
  - tests/test_ticket_land.py::TestReleaseBump::test_stale_worktree_version_bump_yields_main_plus_one
  - tests/test_ticket_land.py::TestReleaseBump::test_downgrade_bump_is_refused
threat: null
component: null
---
Twice today a land recomputed the REL001 version bump from the WORKTREE side and clobbered a higher version already on main: T-0976 reused 0.181.0 (its worktree had reset land-owned files pre-merge) and T-0989 wrote 0.182.0 over main 0.183.0. _apply_release_bump (or its input selection) must read the version from MAIN/root current state at land time -- never from the worktree pyproject that rode through the squash -- and must refuse loudly if the computed next version is <= the version main already has (monotonicity assertion, sibling of T-0959 archive integrity and T-0740 ledger integrity). Regression test: worktree carrying a stale version + main ahead -> land produces main+1, never a downgrade.

Known tooling issue hit and worked around: `frob ticket done-report --why-file`
hung indefinitely for this ticket (bug T-0887, per playbook) -- killed the
hung process and wrote this Done report block directly into tickets.md
instead.