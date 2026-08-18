---
id: T-2485
title: waive-audit complete has no partial-catchup-progress path, defeating the 100-item
  bound
state: done
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
- src/frob/_cli_parsers/_ticket/_closeout.py
- tests/unit/test_waive_audit_runner.py
- tests/unit/test_waive_audit_watermark.py
- docs/modules/app.md
- src/frob/app/config.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: the fix needs a new --partial CLI flag and touches banked-partial-progress
    tests/docs alongside the runner/watermark modules
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_waive_audit_runner.py
  reason: the fix needs a new --partial CLI flag and touches banked-partial-progress
    tests/docs alongside the runner/watermark modules
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_waive_audit_watermark.py
  reason: the fix needs a new --partial CLI flag and touches banked-partial-progress
    tests/docs alongside the runner/watermark modules
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/app.md
  reason: the fix needs a new --partial CLI flag and touches banked-partial-progress
    tests/docs alongside the runner/watermark modules
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/config.py
  reason: WIRE001 requires the new --partial CLI dest to be a declared AppConfig field,
    same as the sibling waive_audit_reviewed_count/waive_audit_cop_outs fields
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/_config_external.py
  reason: AppConfig fields populated from argparse only reach it via _config_external.py's
    field-name tuples (_BOOL_FLAGS); waive_audit_partial needs an entry there or FLAGCOV001/WIRE001
    correctly flag it as parsed-but-never-applied
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_waive_audit_runner.py::TestPartialCatchup::test_partial_without_flag_still_refuses
- tests/unit/test_waive_audit_runner.py::TestPartialCatchup::test_partial_banks_batch_and_advances_watermark
- tests/unit/test_waive_audit_runner.py::TestPartialCatchup::test_next_scan_skips_already_banked_waivers
- tests/unit/test_waive_audit_runner.py::TestPartialCatchup::test_banking_the_final_batch_clears_catchup_state
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-1614's first waive-audit pass (T-2467's mechanism). 'scan' bounds a first-run/catchup pass to _CATCHUP_BOUND=100 waivers and reports not_covered_count for the remainder (this repo: 857 not covered after reviewing 100). But 'complete_pass' (_waive_audit.py) REFUSES unconditionally whenever mode=='catchup' and not_covered_count>0 -- and there is no other code path or CLI flag that ever writes a WaiveAuditWatermark with a nonzero catchup_remaining. WaiveAuditWatermark.catchup_remaining exists and its own docstring says a nonzero value means 'the next pass must continue catch-up rather than treat the repo as fully audited' -- implying partial catch-up progress is meant to be persisted. In the current implementation it is not: the ONLY way to ever save a watermark is to review all 857 waivers in one sitting (defeating the entire point of bounding a pass to 100, which was explicitly built so a huge pre-existing corpus does not hand the first pass an unreviewable pile). Recommend either: (a) a --continue-catchup path on 'complete' that reviews exactly the scanned batch and writes catchup_remaining = not_covered_count (so the NEXT scan's bounded window advances past what was already reviewed, e.g. by tracking a covered-set or an offset), or (b) explicitly document that catch-up review must happen in as many scan/re-classify cycles as needed before ANY complete call, with a single combined --reviewed-count spanning everything -- whichever the T-2467 author intended, since the current code implements neither cleanly. Filed by T-1614's own periodic audit pass rather than fixed inline, since fixing frob's own audit tooling is outside T-1614's declared no-scope pass.