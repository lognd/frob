---
id: T-2716
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2707):
  43 new (rule, file) identit(ies), 45 finding(s) (ARCH103, COV003, COV004, DOC002)'
state: dropped
kind: bug
origin: agent
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/cli.md
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/verify_runner.py
- src/frob/deploy/_audit.py
- src/frob/doctor.py
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/_milestone.py
- src/frob/lang/_support.py
- src/frob/release/_cli.py
- src/frob/scaffold/_skills_sync.py
- src/frob/serve/_socketd.py
- src/frob/strata/_multifile.py
- src/frob/testing/_collect_kotlin.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_store.py
- src/frob/vet/_capability_core.py
- tests/system/test_cli_doctor.py
- tests/test_capability_registry.py
- tests/test_doctor.py
- tests/test_hook_diagnosis_nudge.py
- tests/test_prework_parity.py
- tests/test_release.py
- tests/test_tickets_organization.py
- tests/test_vet.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_doctor_runner_t1276.py
- tests/unit/test_main_entry.py
- tickets.md
- tickets/T-1397
- tickets/T-1526
- tickets/T-1688
- tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
- tickets/T-2365
- tickets/T-2691/ticket.md
- tickets/T-2703/ticket.md
- tickets/T-2705/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: design
  reason: collides with T-2694's live lease on design/frob.strata; SELFAUDIT001 design
    identity deferred separately, not blocking the other 42 identities' re-triage
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2707) at commit e70b60710557ff91e61fa1d804f4ec447019c832 found 43 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (43), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 45 actual finding(s) across those 43 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH103  src/frob/release/_cli.py
- ARCH103  src/frob/tickets/_store.py
- COV003  tickets/T-1397
- COV003  tickets/T-1526
- COV003  tickets/T-1688
- COV003  tickets/T-2365
- COV004  tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- COV004  tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
- DOC002  src/frob/gates/_milestone.py
- DOC006  tickets/T-2691/ticket.md
- DOC006  tickets/T-2703/ticket.md
- DOC006  tickets/T-2705/ticket.md
- DRIFT001  src/frob/_cli_parsers/_ticket/_new.py
- DRIFT001  src/frob/app/ticket_runner/_verify.py
- DRIFT001  src/frob/tickets/__init__.py
- LANG004  src/frob/lang/_support.py
- PERF002  tests/unit/test_main_entry.py
- PERF003  src/frob/gates/_debt_deprecated.py
- PERF003  src/frob/vet/_capability_core.py
- PERF004  src/frob/gates/_milestone.py
- PERF004  src/frob/scaffold/_skills_sync.py
- PERF004  src/frob/testing/_collect_kotlin.py
- PII010  src/frob/deploy/_audit.py
- PII012  src/frob/doctor.py
- PII012  src/frob/serve/_socketd.py
- PII012  tests/system/test_cli_doctor.py
- PII012  tests/test_capability_registry.py
- PII012  tests/test_doctor.py
- PII012  tests/test_hook_diagnosis_nudge.py
- PII012  tests/test_prework_parity.py
- PII012  tests/test_vet.py
- PII012  tests/unit/test_doctor_runner_t1276.py
- RENDER001  src/frob/release/_cli.py
- SEC004  tests/test_tickets_organization.py
- SEC110  src/frob/app/ticket_runner/_verify.py
- SEC110  src/frob/app/verify_runner.py
- SEC110  tests/test_release.py
- SELFAUDIT001  design
- TEST001  src/frob/strata/_multifile.py
- TICK003  tickets.md
- TICK004  tickets.md
- WIRE002  tests/unit/test_app_runners_batch6.py
- WIRE003  docs/modules/cli.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH103  src/frob/release/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/tickets/_store.py  -> attributed to T-2679 (commit 2d5ab2161d63, already closed/dropped -- filed below) via src/frob/tickets/_land.py::_land_locked -> src/frob/tickets/_land_squash.py::_land_squash_apply -> src/frob/tickets/_store.py::_store_mode -> src/frob/tickets/_store.py::_v2_glob
- COV003  tickets/T-1397  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1526  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1688  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-2365  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/gates/_milestone.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  tickets/T-2691/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  tickets/T-2703/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  tickets/T-2705/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/_cli_parsers/_ticket/_new.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/app/ticket_runner/_verify.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['c7e82c8c1e2c0178d783153dd0b3b06279d8552b', '2d5ab2161d6352fa4111c302d98091b16aa814ba']
- DRIFT001  src/frob/tickets/__init__.py  -> attributed to T-2679 (commit 2d5ab2161d63, already closed/dropped -- filed below) via src/frob/tickets/_land.py::_land_locked -> src/frob/tickets/__init__.py::_load_one
- LANG004  src/frob/lang/_support.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  tests/unit/test_main_entry.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/gates/_debt_deprecated.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/vet/_capability_core.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/_milestone.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/scaffold/_skills_sync.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/testing/_collect_kotlin.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII010  src/frob/deploy/_audit.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  src/frob/doctor.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  src/frob/serve/_socketd.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  tests/system/test_cli_doctor.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  tests/test_capability_registry.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  tests/test_doctor.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  tests/test_hook_diagnosis_nudge.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  tests/test_prework_parity.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  tests/test_vet.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  tests/unit/test_doctor_runner_t1276.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- RENDER001  src/frob/release/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC004  tests/test_tickets_organization.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  src/frob/app/ticket_runner/_verify.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['c7e82c8c1e2c0178d783153dd0b3b06279d8552b', '2d5ab2161d6352fa4111c302d98091b16aa814ba']
- SEC110  src/frob/app/verify_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  tests/test_release.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SELFAUDIT001  design  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TEST001  src/frob/strata/_multifile.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK003  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE002  tests/unit/test_app_runners_batch6.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE003  docs/modules/cli.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-20: Re-measured against current main (frob check --json --no-cache, severity read correctly): of 43 (rule,file) identities, 4 no longer reproduce (DOC006 x3, LANG004), 8 PII012/PII010 identities resolved by this same series' T-2712 land, 2 PII012 sites remain live and are already tracked in T-2712's own T-2741 follow-up. The remaining ~29 identities ARE real, reproducing errors -- but nearly all are UNATTRIBUTED (no batch commit's touched symbols reach them), matching this session's finding that T-2713/T-2715's deferred-verification repair surfaced large pre-existing backlogs a budget-truncated check never saw complete before -- there is no single land to revert or blame. The 3 identities WITH real attribution (DRIFT001+SEC110 on _verify.py -> T-2713, confirmed via git show --stat to touch that file directly; DRIFT001 on tickets/__init__.py -> T-2679 via call-chain, already closed/dropped) are cross-cutting doc-drift/capability-declaration fixes, not something to force through this PII-shaped ticket. All ~29 live findings are preserved with full per-identity detail (not silently dropped) in the follow-up ticket this absorbs into. This ticket's own body explicitly permits closing with the pre-existing-residue finding stated when true. (absorbed by T-2743)
