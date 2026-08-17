---
id: T-2278
title: 'DOC005: README/cli.md command table missing sync-skills row (T-2268 triage)'
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
- README.md
- docs/modules/cli.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Both DOC005 identities resolve (sync-skills row present, count claims correct)
    and no longer appear in an unscoped frob check
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2268 holding-ticket triage (2026-08-17): DOC005 fires because README.md's
top-level subcommand table (and docs/modules/cli.md's mirror) is out of
sync with the live subcommand registry -- specifically, `frob sync-skills`
(T-2241) is a real, wired subcommand with no row in either table.

    DOC005  README.md
    DOC005  docs/modules/cli.md

Note: this is a further regression from T-2241's own land, same root cause
as T-2268's already-fixed _skills_sync.py trio (COV001/DOC002/RENDER001),
but it lives in files outside that ticket's declared scope
(src/frob/scaffold/_skills_sync.py only) -- filed separately per T-2268's
own instruction not to widen scope.

Fix: add a `sync-skills` row to both command tables, matching the live
registry (see docs/modules/gates.md's DOC005 section, "README command-
table drift-lock", for the exact format/count-claim convention both files
must satisfy).
