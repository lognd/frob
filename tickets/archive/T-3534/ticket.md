---
id: T-3534
title: Document T-3526's abandoned Tier-A autofix journal detection in docs/modules/gates.md
state: done
kind: docs
origin: human
created: '2026-08-30'
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
- tests/unit/test_fix_engine_journal.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_fix_engine_journal.py
  reason: re-point a stale WIRE001 waiver follow_up=T-3534 citation to its correct
    successor ticket (T-3558) so this docs-only ticket can close
  actor: logan
  at: '2026-08-31'
evidence:
- cmd:grep -c 'Abandoned auto-fix journal detection' docs/modules/gates.md exit=0
  sha256=4355a46b19d3
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3526: apply_tier_a_fixes now journals BEFORE the first handler mutates anything (not only after each completes) and records the writing process's pid; frob.gates._fix_engine_shared.read_abandoned_autofix_manifest and frob.check._abandoned_autofix_result (AUTOFIX001) detect and loudly refuse a journal left behind by a dead process, distinguishing it from one a still-live concurrent --fix process owns. docs/modules/gates.md's existing '--fix Tier-A deterministic auto-fix handlers (T-1138)' anchor (#--fix-tier-a-deterministic-auto-fix-handlers-t-1138) is the natural home for this -- add a subsection describing the journal-before-first-mutation contract, the AutofixManifest model, and the AUTOFIX001 precheck frob check now runs before any stage dispatches. docs/modules/gates.md was leased by in-progress T-3492 at T-3526's filing time so the doc update could not land in the same ticket; AFFECT001 (apply_tier_a_fixes) and COV001 (AutofixManifest) are tracked as frob:debt against this ticket in the interim.