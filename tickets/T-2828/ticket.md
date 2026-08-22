---
id: T-2828
title: 'LARGE001: split or waive oversized frob.gates modules, batch 1 of 2'
state: done
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
- src/frob/gates/__init__.py
- src/frob/gates/_coverage.py
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/_docblocks.py
- src/frob/gates/_docblocks_refs.py
- src/frob/gates/_docptr.py
- src/frob/gates/_fix_engine.py
- src/frob/gates/_fix_engine_sync.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_doclink_docanchor.py
  reason: real seam identified (docstatus/docmake/docseverity bolted onto the documented
    DOC001/DOC002 pair without doc-anchor/re-export verification) but not resolvable
    inside this batch's scope -- filed as its own ticket (T-draft-107afed9, same shape
    as T-2833/T-2834) with the full investigation; this batch's remaining 9 files
    all resolve to severity=note
  actor: logan
  at: '2026-08-21'
body_changes:
- mode: append
  reason: T-2828 land refused with BUG002/EvidenceConfirmatoryOnly since this batch's
    evidence is confirmatory-only for a kind=bug ticket; this IS a comment-only no-behavior-change
    batch (9 frob:waive additions), so declaring that explicitly per the land error's
    own remedy option 2
  actor: logan
  at: '2026-08-21'
  old_length: 1545
  new_length: 1980
evidence:
- tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged
- tests/test_gates.py::TestDebtGate::test_debt002_closed_ticket_is_reported
- tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean
- tests/test_gates.py::TestCov002ScopeCoverage::test_open_ticket_scope_covers_changed_symbol
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

frob:no-behavior-change reason="this batch is comment-only (9 frob:waive LARGE001 directives added, zero code lines changed); no defect fix is claimed for those 9 files -- verified via ast.parse on every touched file plus a full test_gates.py re-run (803/809, 6 pre-existing failures reproduced independently on unmodified main). BUG002's designated-repro requirement does not apply: there is no behavior to reproduce a failure for."