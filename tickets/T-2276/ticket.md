---
id: T-2276
title: 'PERF004: scripts/fleet_status.py has no owning ticket (T-2268 triage)'
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: The PERF004 identity resolves and no longer appears in an unscoped frob check
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2268 holding-ticket triage (2026-08-17): PERF004 fires on
scripts/fleet_status.py with no owning ticket in the unscoped floor.

    PERF004  scripts/fleet_status.py

Note: T-2213 (queued, scope=scripts/fleet_status.py) already owns this
file's ARCH001+COV001 findings on `ticket_readiness`; T-2206 (queued)
already owns a DIFFERENT PERF004 identity in
src/frob/app/ticket_runner/_land_cmd.py, not this one. Neither covers
this file's PERF004 in its own acceptance criteria, so this is filed
separately rather than folded into either -- do not silently assume T-2213
covers it just because it shares a scope glob; its acceptance is scoped to
the ARCH001/COV001 split only.

scripts/fleet_status.py is under a LIVE lease (T-2213 in-progress in
worktree t-2213) as of this filing -- do not start this ticket until that
lease clears; check `frob ticket show T-2213` / fleet status first.

Fix: identify the flagged perf anti-pattern (see docs/modules/gates.md's
PERF004 section for the exact pattern class) and address it once the file
is free.
