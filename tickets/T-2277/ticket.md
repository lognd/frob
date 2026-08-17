---
id: T-2277
title: 'REL001: pyproject.toml release-readiness finding has no owning ticket (T-2268
  triage)'
state: dropped
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: The REL001 identity resolves and no longer appears in an unscoped frob check
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2268 holding-ticket triage (2026-08-17): REL001 (release-readiness) fires
on pyproject.toml in the unscoped floor with no owning ticket.

    REL001  pyproject.toml

pyproject.toml is a land-owned file (docs/guides/agent-playbook.md
section 4b) -- never bump the version or hand-edit it in a worktree;
this ticket's own eventual fix (if REL001's open-debt/expired-deprecation
half is what is firing, not the version-bump half FROB_AGENT already
suppresses) still routes through the normal release tooling
(`frob release` / `frob ticket land`'s own auto-bump), never a manual
edit.

Fix: run `frob release`/`frob check --only release` to see which specific
REL001 sub-condition (open debt past its ceiling, an expired deprecation)
is firing, and resolve that underlying condition.

## Drop reason
- 2026-08-17: Re-measured against current unscoped floor: frob check --only release runs clean (0 findings, no gate:REL output). Neither REL001 sub-condition fires on pyproject.toml today; stale T-2268 triage residue, dropping rather than inventing work
