---
id: T-2156
title: Sweep finding identities carry ABSOLUTE paths so commit attribution always
  fails, every finding reads unattributed, and that raises the quarantine which switches
  deferred landing off fleet-wide
state: queued
kind: bug
origin: human
created: '2026-08-11'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/graph/callgraph.py
- src/frob/verify/_attribution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/verify/
  reason: 'Premise falsified by frob verify explain: attribution failure is NOT caused
    by absolute-vs-relative path shape (a repo-relative finding attributed too, and
    wrongly). Real mechanism is _ordered_private_callees (callgraph.py:443) resolving
    callees through a codebase-wide SHORT-NAME index, so a test defining _run/_commit_all
    gets edges to all 17/18 same-named private helpers across the tree, producing
    false attribution and -- via _attribution.py''s own more-than-one-reaching=unattributed
    rule -- the commit=None findings. Re-scoping to the real files.'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/graph/callgraph.py
  reason: 'Premise falsified by frob verify explain: attribution failure is NOT caused
    by absolute-vs-relative path shape (a repo-relative finding attributed too, and
    wrongly). Real mechanism is _ordered_private_callees (callgraph.py:443) resolving
    callees through a codebase-wide SHORT-NAME index, so a test defining _run/_commit_all
    gets edges to all 17/18 same-named private helpers across the tree, producing
    false attribution and -- via _attribution.py''s own more-than-one-reaching=unattributed
    rule -- the commit=None findings. Re-scoping to the real files.'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/verify/_attribution.py
  reason: 'Premise falsified by frob verify explain: attribution failure is NOT caused
    by absolute-vs-relative path shape (a repo-relative finding attributed too, and
    wrongly). Real mechanism is _ordered_private_callees (callgraph.py:443) resolving
    callees through a codebase-wide SHORT-NAME index, so a test defining _run/_commit_all
    gets edges to all 17/18 same-named private helpers across the tree, producing
    false attribution and -- via _attribution.py''s own more-than-one-reaching=unattributed
    rule -- the commit=None findings. Re-scoping to the real files.'
  actor: logan
  at: '2026-08-11'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
