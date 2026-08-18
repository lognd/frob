# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0001 -->
```yaml
id: T-0001
title: a completed ticket
state: done
kind: bug
origin: human
created: '2026-01-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_example.py::test_thing
designated_repro_test: null
acceptance:
- text: GIVEN a bug WHEN fixed THEN tests pass
  evidence:
  - tests/test_example.py::test_thing
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
```
## Description
some bug that was fixed.

## Done report

Fixed the thing.

### Changed
- src/example.py::thing

### Evidence
- tests/test_example.py::test_thing

<!-- ticket:T-0002 -->
```yaml
id: T-0002
title: a queued follow-up
state: queued
kind: feature
origin: agent
created: '2026-01-02'
priority: medium
blocked_by:
- T-0001
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
attachments:
- path: mockup.txt
  caption: a sample mock
  sha256: deadbeef
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
```
## Description
follow-up work, blocked on T-0001.

<!-- ticket:T-draft-abc12345 -->
```yaml
id: T-draft-abc12345
title: an unlanded draft
state: queued
kind: bug
origin: agent
created: '2026-01-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
```
## Description
filed mid-worktree, not yet renumbered.
