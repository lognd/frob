---
id: T-3177
title: Declare or waive SYS003 scripts_ops -> graphlang in branch_stranded_work_analysis.py
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/branch_stranded_work_analysis.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): SYS003 resolved via frob:waive comment additions
    and a directive-anchor relocation to fix collateral COV001/COV007/TEST001; no
    runtime code path changed, nothing to repro-test against'
  actor: logan
  at: '2026-08-27'
  old_length: 960
  new_length: 1178
- mode: append
  reason: 'BUG002 front door (T-2393): SYS003 resolved via frob:waive comment additions
    and a directive-anchor relocation to fix collateral COV001/COV007/TEST001; no
    runtime code path changed, nothing to repro-test against'
  actor: logan
  at: '2026-08-27'
  old_length: 1178
  new_length: 1396
- mode: append
  reason: 'BUG002 front door (T-2393): SYS003 resolved via frob:waive comment additions
    and a directive-anchor relocation to fix collateral COV001/COV007/TEST001; no
    runtime code path changed, nothing to repro-test against'
  actor: logan
  at: '2026-08-27'
  old_length: 1178
  new_length: 1396
evidence:
- tests/unit/test_branch_stranded_work_analysis.py::TestTicketIdsOnBranch::test_ledger_path_yields_its_own_id
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: dfe0fb6da62916e09aa18e7d46af140920c6382b
---
scripts/branch_stranded_work_analysis.py:287-289 imports frob.graph.EdgeKind, frob.graph.dsl.parse_directives, and frob.lang.parse_file inside a try/except ImportError fallback -- an undeclared cross-component import (scripts_ops -> graphlang) per SYS003. This is a separate, pre-existing case from T-3172's __init__.py re-export findings (same rule, unrelated file/reason -- not folded into that ticket per the coordinator's explicit instruction). scripts/measure_evidence_reach.py has the identical shape (frob.graph/frob.graph.reach imports) and already carries a frob:waive with a 'one-off measurement-script exemption' reason; this file's import is not currently waived at all. Resolve by either declaring a scripts_ops -> graphlang Flow in design/frob.strata, or adding the matching frob:waive SYS003 if the one-off-script exemption reasoning applies here too.

## Reopen log
- 2026-08-27: land refused: needs bound evidence/no-behavior-change front door

frob:no-behavior-change reason="SYS003 resolved via frob:waive comment additions and a directive-anchor relocation to fix collateral COV001/COV007/TEST001; no runtime code path changed, nothing to repro-test against"

frob:no-behavior-change reason="SYS003 resolved via frob:waive comment additions and a directive-anchor relocation to fix collateral COV001/COV007/TEST001; no runtime code path changed, nothing to repro-test against"