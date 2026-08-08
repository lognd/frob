---
id: T-1832
title: Document T-1821's symbolic DirtyMain attribution in docs/modules/tickets.md
state: queued
kind: docs
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1821 added symbolic DirtyMain attribution (`_staged_rapid_debt_ticket`,
`describe_root_dirt`'s sweep_hint now names the real ticket id read off a
staged `rapid-debt.jsonl` line, falling back to "unattributed" rather
than a plausible-but-wrong guess) but could not update
`docs/modules/tickets.md`'s "Deferred post-land sweep" section
(AFFECT001's own doc anchor for `describe_root_dirt`) because that file
is out of T-1821's declared scope and held by another concurrent agent
per this session's dispatch.

Add a short paragraph to
docs/modules/tickets.md#deferred-post-land-sweep-rapid-only-t-1684
documenting `_staged_rapid_debt_ticket` and the "unattributed" fallback,
then remove the AFFECT001 waiver on
src/frob/tickets/_land_git_ops.py::describe_root_dirt.
