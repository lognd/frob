---
id: T-2743
title: Repo-wide pre-existing debt surfaced by T-2713/T-2715's deferred-verification
  repair (from T-2716 re-triage)
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/release/_cli.py
- src/frob/tickets/_store.py
- tickets/T-1397
- tickets/T-1526
- tickets/T-1688
- tickets/T-2365
- tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
- src/frob/gates/_milestone.py
- tests/unit/test_main_entry.py
- src/frob/gates/_debt_deprecated.py
- src/frob/vet/_capability_core.py
- src/frob/scaffold/_skills_sync.py
- src/frob/testing/_collect_kotlin.py
- tests/test_tickets_organization.py
- src/frob/app/verify_runner.py
- tests/test_release.py
- design
- src/frob/strata/_multifile.py
- tickets.md
- tests/unit/test_app_runners_batch6.py
- docs/modules/cli.md
- src/frob/app/ticket_runner/_verify.py
- src/frob/tickets/__init__.py
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
T-2716 was an auto-filed post-land sweep regression ticket (43 (rule,
file) identities, 45 findings) attributed to "sweep spawned by T-2707".
Re-measured against current main (`frob check --json --no-cache`,
severity read at the correct diagnostics[].severity level, not a grep
count) rather than assumed from a similar-shaped prior ticket. Findings
below are REAL, currently-reproducing errors -- this is not an
attribution-is-wrong dismissal (T-2716 is NOT being closed as false
alarm; see its own closure reasoning).

Per-identity disposition:

RESOLVED (no longer reproduce, no action needed):
- DOC006 tickets/T-2691/ticket.md, T-2703/ticket.md, T-2705/ticket.md
- LANG004 src/frob/lang/_support.py

RESOLVED by T-2712's land (this same series, symref path-prefix +
directive-continuation + email-TLD + wrapped-marker fixes to
src/frob/gates/_pii_structural/**) -- now waived at NOTE severity:
- PII010 src/frob/deploy/_audit.py
- PII012 src/frob/doctor.py, tests/system/test_cli_doctor.py,
  tests/test_doctor.py, tests/test_hook_diagnosis_nudge.py,
  tests/test_prework_parity.py, tests/test_vet.py,
  tests/unit/test_doctor_runner_t1276.py

STILL LIVE, already tracked in a separate follow-up (T-2741, filed by
T-2712 -- do not duplicate):
- PII012 src/frob/serve/_socketd.py:530 (waiver bound to the wrong
  symbol by the comment-binding DSL)
- PII012 tests/test_capability_registry.py:902 (missing waiver,
  "secretsmanager" false positive)

STILL LIVE, genuine cross-cutting debt, UNATTRIBUTED to any specific
land (matches this session's own finding that T-2713/T-2715's repair
of the deferred-verification budget-truncation surfaced large
pre-existing backlogs never seen by a complete scan before -- these
carry no reachable batch-commit attribution, meaning no single land is
at fault and there is nothing to revert):
- ARCH103 src/frob/release/_cli.py:60, src/frob/tickets/_store.py:1360
- COV003 tickets/T-1397, T-1526, T-1688, T-2365 (evidence node id
  does not resolve against the current test suite)
- COV004 tickets/T-2195/attachments/02-..., T-2328/attachments/01-...
  (attachment sha drift)
- DOC002 src/frob/gates/_milestone.py:331 (frob:doc anchor does not
  resolve)
- PERF002 tests/unit/test_main_entry.py:359
- PERF003 src/frob/gates/_debt_deprecated.py:725,
  src/frob/vet/_capability_core.py:624,662
- PERF004 src/frob/gates/_milestone.py:142,240,359,
  src/frob/scaffold/_skills_sync.py:277,
  src/frob/testing/_collect_kotlin.py:241
- RENDER001 src/frob/release/_cli.py:77,81,82,84
- SEC004 tests/test_tickets_organization.py:43 (frob:secret-fake
  missing reason=)
- SEC110 src/frob/app/verify_runner.py:352,354,
  tests/test_release.py:899
- SELFAUDIT001 design (14 findings)
- TEST001 src/frob/strata/_multifile.py:206
- TICK003/TICK004 tickets.md (5 findings)
- WIRE002 tests/unit/test_app_runners_batch6.py:530
- WIRE003 docs/modules/cli.md

STILL LIVE, WITH real attribution (blamed commit confirmed via `git
show --stat` to actually touch the named file -- this attribution IS
correct, not a false-attribution case):
- DRIFT001 + SEC110 src/frob/app/ticket_runner/_verify.py -- both
  attributed to T-2713's land commit c7e82c8c1e2c0178d783153dd0b3b06
  279d8552b, confirmed via `git show --stat` to modify
  src/frob/app/ticket_runner/_verify.py directly (103 lines changed).
- DRIFT001 src/frob/tickets/__init__.py -- attributed to T-2679's
  land commit 2d5ab2161d6352fa4111c302d98091b16aa814ba via a call-
  chain (_land.py::_land_locked -> tickets/__init__.py::_load_one),
  not a direct file touch (T-2679's own diff only modifies
  src/frob/tickets/_land.py) -- symbolic-reachability attribution,
  not a mistaken direct-touch claim. T-2679 itself is already closed/
  dropped per the sweep's own note.

This backlog spans ARCH/COV/DOC/PERF/RENDER/SEC/SELFAUDIT/TEST/TICK/
WIRE -- no shared root cause the way T-2712's PII group had one; each
needs its own subsystem-owner fix. Filed as one tracking ticket rather
than left to re-appear silently in the next sweep. Scope intentionally
left broad (matches the files above) for whoever triages next to
narrow per T-2302's scope_breadth_ack discipline before starting.
