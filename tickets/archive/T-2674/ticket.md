---
id: T-2674
title: 'Persistent unfixed repo-debt tracking (continuation of T-2653): 37 identit(ies)
  remaining'
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/commands/release.md
- docs/modules/cli.md
- docs/modules/gates.md
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/verify_runner.py
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/_milestone.py
- src/frob/release/_cli.py
- src/frob/scaffold/_skills_sync.py
- src/frob/strata/_multifile.py
- src/frob/testing/_collect_kotlin.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_store.py
- src/frob/vet/_capability_core.py
- tests/test_capability_registry.py
- tests/test_release.py
- tests/test_tickets_organization.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_main_entry.py
- tickets.md
- tickets/T-1397
- tickets/T-1526
- tickets/T-1688
- tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
- tickets/T-2344
- tickets/T-2348
- tickets/T-2365
- tickets/T-2570/ticket.md
- docs/index.md
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/index.md
  reason: 'DOC001 fix: docs/commands/release.md was linked from nowhere; adding it
    to the docs/commands table in docs/index.md, same pattern every sibling command
    doc already uses'
  actor: logan
  at: '2026-08-19'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 883ca5ba222ff643dcefc96cfc9f01d7a924f144
---
TRACKING TICKET, continuation of T-2653 (closed by its own land, which
always closes the ticket it lands -- this ticket carries forward the
37 identities T-2653's first batch did not clear).

T-2653 (5 identities: COV001 fmt_runner.py, COV001 _refs_schema.py,
COV001 _rule_id_scan.py, COV001 _multifile.py, DOC002 _refs_schema.py)
landed at 801d0ffddcca3bdfed969d111a58d7fb5c3f5ea1 -- see its Done
report for the full before/after verification.

## Remaining tracked identities (37), live-reproduction status as of
## T-2653's own triage (2026-08-19, full unscoped frob check --json)

- ARCH103  src/frob/release/_cli.py  -- LIVE
- ARCH103  src/frob/tickets/_store.py  -- LIVE
- COV003  tickets/T-1397  -- LIVE
- COV003  tickets/T-1526  -- LIVE
- COV003  tickets/T-1688  -- LIVE
- COV003  tickets/T-2344  -- LIVE
- COV003  tickets/T-2348  -- LIVE
- COV003  tickets/T-2365  -- LIVE
- COV004  tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md  -- LIVE
- COV004  tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md  -- LIVE
- DOC001  docs/commands/release.md  -- LIVE
- DOC002  src/frob/gates/_milestone.py  -- LIVE
- DOC005  docs/modules/cli.md  -- LIVE
- DOC006  tickets/T-2570/ticket.md  -- LIVE
- DOC008  docs/modules/gates.md  -- re-verify (T-2670 landed a gates.md
  fix mid-session; may already be resolved)
- DOCENUM001  docs/modules/gates.md  -- re-verify (same as DOC008)
- DRIFT001  src/frob/_cli_parsers/_ticket/_new.py  -- LIVE
- DRIFT001  src/frob/app/ticket_runner/_verify.py  -- re-verify (T-2668
  landed a _verify.py fix mid-session for a different defect; may have
  moved this digest again)
- DRIFT001  src/frob/tickets/__init__.py  -- LIVE
- F401  src/frob/app/ticket_runner/__init__.py  -- NOT LIVE at T-2653's
  triage; re-confirm before dropping this identity
- LANG004  src/frob/lang/_support.py  -- NOT LIVE at T-2653's triage;
  re-confirm before dropping this identity
- PERF002  tests/unit/test_main_entry.py  -- LIVE
- PERF003  src/frob/gates/_debt_deprecated.py  -- LIVE
- PERF003  src/frob/vet/_capability_core.py  -- LIVE
- PERF004  src/frob/app/ticket_runner/_new.py  -- LIVE
- PERF004  src/frob/gates/_milestone.py  -- LIVE
- PERF004  src/frob/scaffold/_skills_sync.py  -- LIVE
- PERF004  src/frob/testing/_collect_kotlin.py  -- LIVE
- PII012  tests/test_capability_registry.py  -- LIVE
- RENDER001  src/frob/release/_cli.py  -- LIVE
- SEC004  tests/test_tickets_organization.py  -- LIVE
- SEC110  src/frob/app/ticket_runner/_verify.py  -- LIVE
- SEC110  src/frob/app/verify_runner.py  -- LIVE
- SEC110  tests/test_release.py  -- LIVE
- SELFAUDIT001  design  -- LIVE, but EXCLUDED from this ticket's own
  fixable scope while T-2666 holds design/frob.strata's lease (the
  SYS107/testsuite-exec finding this bundles is T-2666's own subject)
- TEST001  src/frob/strata/_multifile.py  -- LIVE
- TICK003  tickets.md  -- LIVE
- TICK004  tickets.md  -- LIVE
- WIRE002  tests/unit/test_app_runners_batch6.py  -- LIVE
- WIRE003  docs/modules/cli.md  -- LIVE

frob:no-behavior-change reason="Same posture as T-2653: this ticket's
groups (COV003/COV004 evidence-node drift, DOC001/002/005/008 +
DOCENUM001 doc-anchor drift, TICK003/004 ledger metadata, and similar)
are additive metadata/doc-anchor fixes with zero runtime behavior
change. Any batch that turns out to be a genuine behavior bug will
bind and designate its own real BUG002 repro test, not rely on this."

Work whichever groups are cleanly fixable; land in coherent batches,
not all 37 at once. File a follow-up for anything needing a design
decision.