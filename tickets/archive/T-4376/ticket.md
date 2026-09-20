---
id: T-4376
title: 'SELFAUDIT001: _ledger_mirror.py''s new fs.read call sites (T-3892) not declared
  in design/frob.strata'
state: dropped
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
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
T-3892's evidence-union fix (_mirror_evidence_union, _mirror_ledger_paths in src/frob/app/ticket_runner/_ledger_mirror.py) added two new Path.read_text() call sites. gate:SELFAUDIT SELFAUDIT001 flags both as an undeclared fs.read capability under the cli self-audit family (SYS100) -- the diagnostic is anchored to design:1, not the source line, so a frob:waive comment in the source file (attempted, see _ledger_mirror.py's two SELFAUDIT001 waive comments) does not clear it; the via-list itself needs a design/frob.strata edit adding src/frob/app/ticket_runner/_ledger_mirror.py to whichever fs.read may-block already covers its existing fs.write declaration (line 139's block covers fs.write for this same file already). Deferred out of T-3892's own declared scope (_ledger_mirror.py, its test file, and one tickets-lifecycle.md doc note) rather than editing the repo-wide design file blind.

## Drop reason
- 2026-09-09: superseded: fixed inline in T-3892 by adding _ledger_mirror.py to design/frob.strata's existing fs.read via-list, since the finding was land-blocking for T-3892's own diff
