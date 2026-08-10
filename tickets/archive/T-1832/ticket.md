---
id: T-1832
title: Document T-1821's symbolic DirtyMain attribution in docs/modules/tickets.md
state: done
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
- src/frob/tickets/_land_git_ops.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: plan requires removing the AFFECT001 waiver this ticket's doc paragraph
    resolves
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_the_real_ticket_from_a_staged_rapid_debt_line
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_unattributed_when_the_true_author_cannot_be_determined
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
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