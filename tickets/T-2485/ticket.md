---
id: T-2485
title: waive-audit complete has no partial-catchup-progress path, defeating the 100-item
  bound
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_waive_audit.py
- src/frob/gates/_waive_audit_watermark.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-1614's first waive-audit pass (T-2467's mechanism). 'scan' bounds a first-run/catchup pass to _CATCHUP_BOUND=100 waivers and reports not_covered_count for the remainder (this repo: 857 not covered after reviewing 100). But 'complete_pass' (_waive_audit.py) REFUSES unconditionally whenever mode=='catchup' and not_covered_count>0 -- and there is no other code path or CLI flag that ever writes a WaiveAuditWatermark with a nonzero catchup_remaining. WaiveAuditWatermark.catchup_remaining exists and its own docstring says a nonzero value means 'the next pass must continue catch-up rather than treat the repo as fully audited' -- implying partial catch-up progress is meant to be persisted. In the current implementation it is not: the ONLY way to ever save a watermark is to review all 857 waivers in one sitting (defeating the entire point of bounding a pass to 100, which was explicitly built so a huge pre-existing corpus does not hand the first pass an unreviewable pile). Recommend either: (a) a --continue-catchup path on 'complete' that reviews exactly the scanned batch and writes catchup_remaining = not_covered_count (so the NEXT scan's bounded window advances past what was already reviewed, e.g. by tracking a covered-set or an offset), or (b) explicitly document that catch-up review must happen in as many scan/re-classify cycles as needed before ANY complete call, with a single combined --reviewed-count spanning everything -- whichever the T-2467 author intended, since the current code implements neither cleanly. Filed by T-1614's own periodic audit pass rather than fixed inline, since fixing frob's own audit tooling is outside T-1614's declared no-scope pass.