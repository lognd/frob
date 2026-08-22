---
id: T-2685
title: 'Persistent unfixed repo-debt tracking (continuation of T-2674): 35 identit(ies)
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
- docs/modules/gates.md
- src/frob/_cli_parsers/_ticket/_new.py
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
evidence_scope:
- tests/unit/gates/test_lexical_selfcheck.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_supplychain_lexcheck001_backlog_is_empty_t2469
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 62e8129ae7851bc0aeafd36c22bdb0babdba2cc8
---
TRACKING TICKET, continuation of T-2674 (closed by its own land, which
always closes the ticket it lands -- carries forward the 35 identities
T-2674's batch did not clear).

Lineage: T-2592+T-2594 consolidated into T-2653 (landed
801d0ffddcca3bdfed969d111a58d7fb5c3f5ea1, cleared 5) -> T-2674 (landed
883ca5ba222ff643dcefc96cfc9f01d7a924f144, cleared 2: DOC001, DOC005).
7 of 42 original identities cleared across two batches so far.

## Remaining tracked identities (35), live-reproduction status as of
## T-2653's original triage (2026-08-19); RE-VERIFY each before
## working it, some may have moved since (T-2670/T-2668 both landed
## fixes touching adjacent files mid-session)

- ARCH103  src/frob/release/_cli.py
- ARCH103  src/frob/tickets/_store.py
- COV003  tickets/T-1397
- COV003  tickets/T-1526
- COV003  tickets/T-1688
- COV003  tickets/T-2344
- COV003  tickets/T-2348
- COV003  tickets/T-2365
- COV004  tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- COV004  tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
- DOC002  src/frob/gates/_milestone.py
- DOC006  tickets/T-2570/ticket.md
- DOC008  docs/modules/gates.md  -- re-verify, T-2670 landed a
  gates.md fix mid-session
- DOCENUM001  docs/modules/gates.md  -- re-verify, same as DOC008
- DRIFT001  src/frob/_cli_parsers/_ticket/_new.py
- DRIFT001  src/frob/app/ticket_runner/_verify.py  -- re-verify,
  T-2668 landed a _verify.py fix mid-session for a different defect
- DRIFT001  src/frob/tickets/__init__.py
- F401  src/frob/app/ticket_runner/__init__.py  -- NOT LIVE at
  original triage; re-confirm before dropping
- LANG004  src/frob/lang/_support.py  -- NOT LIVE at original triage;
  re-confirm before dropping
- PERF002  tests/unit/test_main_entry.py
- PERF003  src/frob/gates/_debt_deprecated.py
- PERF003  src/frob/vet/_capability_core.py
- PERF004  src/frob/app/ticket_runner/_new.py
- PERF004  src/frob/gates/_milestone.py
- PERF004  src/frob/scaffold/_skills_sync.py
- PERF004  src/frob/testing/_collect_kotlin.py
- PII012  tests/test_capability_registry.py
- RENDER001  src/frob/release/_cli.py
- SEC004  tests/test_tickets_organization.py
- SEC110  src/frob/app/ticket_runner/_verify.py
- SEC110  src/frob/app/verify_runner.py
- SEC110  tests/test_release.py
- SELFAUDIT001  design  -- EXCLUDED while T-2666 holds design/frob.strata's lease
- TEST001  src/frob/strata/_multifile.py
- TICK003  tickets.md
- TICK004  tickets.md
- WIRE002  tests/unit/test_app_runners_batch6.py
- WIRE003  docs/modules/cli.md

frob:no-behavior-change reason="Same posture as T-2653/T-2674: this
ticket's groups are additive metadata/doc-anchor fixes with zero
runtime behavior change. Any batch that turns out to be a genuine
behavior bug will bind and designate its own real BUG002 repro test,
not rely on this."

Work whichever groups are cleanly fixable; land in coherent batches.
File a follow-up for anything needing a design decision.