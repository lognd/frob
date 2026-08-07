---
id: T-1460
title: TICK009 scope-breadth cleanup drive
state: done
kind: docs
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:grep -c TICK009 /tmp/claude-1000/-home-logan-projects-frob/c7b9d8f4-5267-4857-94a4-8cf17aa2f513/scratchpad/tick009-mid2.txt
  exit=0 sha256=6169555d9248
designated_repro_test: null
threat: null
component: null
---
TICK009 nudge count sat at 83 outstanding scope-breadth findings across 41
tickets (2026-08-02 measurement). This ticket tracks a ledger-only pass
narrowing QUEUED tickets' overly-broad scope globs to real file lists (or
adding the missing counterpart globs the nudge names), per the TICK009
remediation the finding text itself describes. Tickets already in-progress
this wave (T-1400, T-1415, T-1420) are left untouched. Genuine epic-
umbrella tickets whose broad scope is intentional get a per-nudge waive
note instead of a narrow, not a blanket waiver.

No source edits -- tickets.md scope_changes audit trail only.