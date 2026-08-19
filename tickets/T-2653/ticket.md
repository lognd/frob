---
id: T-2653
title: 'post-land sweep regression from T-2638: 45 new (rule, file) identit(ies),
  71 finding(s) (ARCH103, COV001, COV003, COV004)'
state: queued
kind: bug
origin: agent
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design
- docs/commands/release.md
- docs/modules/cli.md
- docs/modules/gates.md
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/app/fmt_runner.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/verify_runner.py
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/_milestone.py
- src/frob/gates/_refs_schema.py
- src/frob/gates/_rule_id_scan.py
- src/frob/lang/_support.py
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'T-2669 dispatch triage: consolidate T-2592+T-2594 into this ticket per
    coordinator decision; correct the false T-2638-blame the stored title carries;
    document the identity-union computation and confirm no identity resisted consolidation'
  actor: logan
  at: '2026-08-19'
  old_length: 9164
  new_length: 6542
- mode: set
  reason: 'T-2669 dispatch triage: consolidate T-2592+T-2594 into this ticket per
    coordinator decision; correct the false T-2638-blame the stored title carries;
    document the identity-union computation and confirm no identity resisted consolidation'
  actor: logan
  at: '2026-08-19'
  old_length: 6542
  new_length: 6542
- mode: set
  reason: 'T-2669 dispatch triage: consolidate T-2592+T-2594 into this ticket per
    coordinator decision; correct the false T-2638-blame the stored title carries;
    document the identity-union computation and confirm no identity resisted consolidation'
  actor: logan
  at: '2026-08-19'
  old_length: 6542
  new_length: 6542
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TRACKING TICKET for a persistent, unfixed repo-debt set -- NOT a
regression caused by one land. The stored title ("post-land sweep
regression from T-2638") is INHERITED and WRONG: T-2638's land
(ce3f40932b9af175bfb6c2a6964a0bab14a86e19) touches only CHANGELOG.md,
changelog.d/T-2638.md, docs/modules/tickets-data-storage.md,
rapid-debt.jsonl, src/frob/tickets/_reporting.py,
tests/unit/test_reporting_t1648_remainder.py, and its own ticket/
done-report files -- NONE of the identities below. This ticket is kept
open under its original id (no `frob ticket` retitle verb exists in
this repo; retitling would require a hand-edit of the ledger front
matter, which the playbook and T-0574 both forbid) but this body is
now the source of truth for what it tracks. Retained rather than
retitled: whoever reads the stored title next should read THIS
paragraph first.

## Origin (T-2669 dispatch triage, 2026-08-19)

T-2592, T-2594, and T-2653 were filed independently by three separate
post-land sweeps against three unrelated, single-purpose lands
(T-2197, T-2582, T-2638 respectively) -- none of which touched any of
the flagged files (confirmed via `git show --stat` on all three
blamed commits). The false ATTRIBUTION mechanism itself is filed
separately as T-2672. What the three tickets share is not a common
cause but a common EFFECT: the same underlying, never-fixed debt kept
getting rediscovered by successive sweeps and re-filed against
whichever land happened to run next, because nobody had fixed the
debt itself since T-2592 first surfaced it (2026-08-19 00:39).

Per coordinator decision: T-2653 (most complete, most recent) is the
CONSOLIDATION SURVIVOR. T-2592 and T-2594 are dropped as duplicates-
with-a-named-survivor (NOT false positives -- their findings are real,
see LIVE below; only their standalone existence is redundant with this
ticket).

## Union computed across all three source tickets

T-2592 (43 identities) union T-2594 (34) union T-2653 (45) = every
identity in T-2653's own list below PLUS two identities that appeared
ONLY in T-2592/T-2594 and were confirmed NOT LIVE on current main
(2026-08-19, full unscoped `frob check --json`, zero BUDGET001
deferrals):

- DOC006  tickets/T-2585/ticket.md  (in T-2592 and T-2594, absent
  from T-2653) -- re-measured: NOT reproducing, `gate:DOC`'s only
  current DOC006 finding is tickets/T-2570/ticket.md (already listed
  below). Deliberately NOT carried into this ticket's tracked set --
  carrying a confirmed-dead identity into a live-debt tracker would
  misrepresent it as still owed.
- E501  src/frob/app/ticket_runner/_ledger_mirror.py,
  src/frob/app/ticket_runner/_verify.py, src/frob/scaffold/project.py
  (in T-2592 and/or T-2594, absent from T-2653) -- re-measured: E501
  is absent REPO-WIDE right now (`ruff check` reports zero E501
  findings anywhere, only I001 import-sort warnings exist). Same
  reasoning: not carried into the tracked set below.

Nothing else was missing from T-2653's own list -- it already covers
every OTHER identity either source ticket carried. No identity
"resisted consolidation"; the two exclusions above are confirmed dead,
not ambiguous.

## Tracked identities (42), with live-reproduction status as of this
## triage (full unscoped `frob check --json`, current main)

- ARCH103  src/frob/release/_cli.py  -- LIVE
- ARCH103  src/frob/tickets/_store.py  -- LIVE
- COV001  src/frob/app/fmt_runner.py  -- LIVE
- COV001  src/frob/gates/_refs_schema.py  -- LIVE
- COV001  src/frob/gates/_rule_id_scan.py  -- LIVE
- COV001  src/frob/strata/_multifile.py  -- LIVE
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
- DOC002  src/frob/gates/_refs_schema.py  -- LIVE
- DOC005  docs/modules/cli.md  -- LIVE
- DOC006  tickets/T-2570/ticket.md  -- LIVE
- DOC008  docs/modules/gates.md  -- LIVE
- DOCENUM001  docs/modules/gates.md  -- LIVE
- DRIFT001  src/frob/_cli_parsers/_ticket/_new.py  -- LIVE
- DRIFT001  src/frob/app/ticket_runner/_verify.py  -- LIVE
- DRIFT001  src/frob/tickets/__init__.py  -- LIVE
- F401  src/frob/app/ticket_runner/__init__.py  -- NOT LIVE (re-measured
  clean; verify once more before closing this one identity out)
- LANG004  src/frob/lang/_support.py  -- NOT LIVE (re-measured clean;
  verify once more before closing this one identity out)
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
- SELFAUDIT001  design  -- LIVE
- TEST001  src/frob/strata/_multifile.py  -- LIVE
- TICK003  tickets.md  -- LIVE
- TICK004  tickets.md  -- LIVE
- WIRE002  tests/unit/test_app_runners_batch6.py  -- LIVE
- WIRE003  docs/modules/cli.md  -- LIVE

40 of 42 are confirmed LIVE right now; 2 (F401, LANG004) were NOT LIVE
at this triage pass and may already be resolved -- confirm with a
fresh targeted check before dropping them from this ticket's tracked
set, do not just trust this one measurement.

## Working this ticket

Group by rule and land in coherent batches, not one giant change:
COV001 (4 files, missing frob:doc edges), ARCH103 (2 files), COV003
(6 old ticket dirs, evidence-node drift), DOC001/002/005/008 +
DOCENUM001 (doc-anchor drift), PERF002-004 (perf-lint findings, 6
files), DRIFT001 (3 files, digest-moved-since-ack), TICK003/004
(tickets.md), SEC004/SEC110/PII012/SELFAUDIT001/TEST001/RENDER001/
WIRE002/WIRE003 (one file each, likely independent). File a follow-up
for anything that needs a design decision rather than forcing it.
