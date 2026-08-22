---
id: T-2883
title: 'docs/modules/gates.md: document T-2870''s BUG002 malformed-waiver diagnostic'
state: done
kind: docs
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/gates.md
- src/frob/gates/_bug_repro.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_bug_repro.py
  reason: 'T-2883: removing the now-inert frob:waive AFFECT001 placeholder left by
    T-2870 once the doc paragraph it deferred is written'
  actor: logan
  at: '2026-08-22'
evidence:
- cmd:/tmp/t2883_verify.sh exit=0 sha256=73562f782534
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 7b4451dfc3f571586c31b437a479c396499c5fe9
---
T-2870 (BUG002 ticket-body waiver regex silently ignoring an unquoted/malformed reason= value) added _bug002_malformed_waiver to src/frob/gates/_bug_repro.py and a frob:waive AFFECT001 on bug_repro_violations, because docs/modules/gates.md was under T-2874's live scope lease at the time and could not be claimed. Once that lease clears, add the doc paragraph documenting the new malformed-waiver diagnostic to the BUG002 section (right after the existing 'Escape hatch, required and loud' paragraph) and remove the frob:waive AFFECT001 placeholder. See T-2870's Done report for the exact narrative already drafted (it was written once, into docs/modules/gates.md, then reverted only because of the lease conflict -- recovering it from T-2870's git history/Done report is faster than re-deriving it).