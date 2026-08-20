---
id: T-2758
title: 'DOC011: docs/modules/tickets-verify-sweep.md cites phantom T-2736 without
  a waiver'
state: done
kind: docs
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-verify-sweep.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: 'actually a docs-only fix (wrapped a bare ticket-id citation in backticks);
    needed for cmd: evidence eligibility'
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): doc-only false-positive fix: wraps a bare-prose
    ticket-id citation in backticks so DOC011''s code-span exemption applies; no runtime
    code path changed'
  actor: logan
  at: '2026-08-20'
  old_length: 523
  new_length: 707
kind_history:
- 2026-08-20 bug->docs evidence=0 done_report=yes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2744's own doc update (docs/modules/tickets-verify-sweep.md, quarantine circuit breaker section) narrates the T-2736 phantom-ticket incident by name, which trips DOC011 (cites a ticket id that does not resolve in tickets.md/tickets-archive.md) since T-2736 genuinely never existed -- that absence is the whole point of the incident being documented. Needs a frob:waive DOC011 (or equivalent) at that citation with a reason explaining it is a deliberate historical reference to a nonexistent id, not a stale/typo citation.

frob:no-behavior-change reason="doc-only false-positive fix: wraps a bare-prose ticket-id citation in backticks so DOC011's code-span exemption applies; no runtime code path changed"