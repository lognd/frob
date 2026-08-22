---
id: T-2827
title: 'LARGE001: split or waive oversized frob.gates modules, batch 2 of 2'
state: in-progress
kind: bug
origin: agent
created: '2026-08-21'
priority: medium
parent: T-2375
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fmt_directives.py
- src/frob/gates/_gate_cache.py
- src/frob/gates/_lang_conformance.py
- src/frob/gates/_mutation_evidence.py
- src/frob/gates/_protocol_summary.py
- src/frob/gates/_refs.py
- src/frob/gates/_registry_exhaustiveness.py
- src/frob/gates/_tickets_gate.py
- src/frob/gates/_wire.py
- tickets/T-draft-85a71cb2/ticket.md
evidence_scope:
- tests/test_gates.py
- tests/test_gates_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-draft-85a71cb2/ticket.md
  reason: filed a follow-up draft ticket from within this ticket's own worktree; SCOPE001
    requires it in scope
  actor: logan
  at: '2026-08-22'
body_changes:
- mode: append
  reason: add no-behavior-change directive before landing
  actor: logan
  at: '2026-08-22'
  old_length: 1545
  new_length: 2260
evidence:
- tests/test_gates.py::TestWireGate::test_wire002_clean_when_follow_up_ticket_is_open
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_warn_for_feature_kind
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-2375 (LARGE001 burn-down epic). Measured 2026-08-21 via 'frob check --json --budget 500' (severity=warning, code=LARGE001) -- do NOT trust this ticket's own file list without re-measuring first; the tree moves. Each file listed here exceeds frob.toml's max_file_lines=800 threshold.

Per-file disposition is a JUDGMENT CALL, not a mechanical split: T-1651 already established that several LARGE001 files in this repo (_models.py, _waive.py, _land_git_ops.py, check_runner.py, config.py, sys_runner.py -- NOT in this batch, already resolved via frob:waive) are cohesive single-concern files where a line-count split would cut a real seam apart and be STRICTLY WORSE than the warning. For each file in this batch: either (a) find a genuine consumer-set/responsibility seam and split it, or (b) if no real seam exists, add a 'frob:waive LARGE001 reason="..."' with the same rigor T-1651's own waivers show (naming why no split is a real seam, not just 'it is big'). Both are valid closure for a given file; a forced split with no real boundary is not.

Do NOT touch src/frob/strata/_selfconform.py -- it is T-2729's own ticket (largest LARGE001 offender, 2290 lines), already filed, do not absorb it here.

Closure for this CHILD ticket: every file below reads as severity=note (waived) or disappears from LARGE001 entirely when re-measured. Do NOT flip LARGE001 warning->error severity here -- that promotion is T-2375's own final step, deferred until every sibling batch lands (promoting early reds main for siblings' still-open debt).

frob:no-behavior-change reason="comment-only fix -- 9 frob:waive LARGE001 directives added across src/frob/gates/_fmt_directives.py, _gate_cache.py, _lang_conformance.py, _mutation_evidence.py, _protocol_summary.py, _refs.py, _registry_exhaustiveness.py, _tickets_gate.py, _wire.py, zero code lines changed; no defect fix is claimed for any file's logic. Verified via ast.parse on every touched file plus a full tests/test_gates.py + tests/test_gates_mutation_evidence.py run (803/809 collected, 6 pre-existing failures reproduced byte-for-byte on unmodified main with none of this ticket's changes present). BUG002's designated-repro requirement does not apply: there is no behavior to reproduce a failure for."