---
id: T-2341
title: Fix 19 genuinely-new gate findings from T-2299/T-2331 sweep (ARCH001/ARCH103/COV001/COV003/DOC001/DOC002/PERF004/SELFAUDIT001/TICK004/WIRE003)
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- src/frob/app/verify_runner.py
- src/frob/tickets/_land_git_ops.py
- src/frob/verify/_quarantine.py
- docs/modules/cli.md
- docs/guides/coordinator-scripts.md
- design/**
- tickets.md
- docs/modules/tickets-landing.md
evidence_scope:
- tests/unit/test_coordinator_scripts.py
- tests/unit/verify/test_quarantine.py
- tests/unit/test_land_duplicate_ticket_id.py
- tests/system/test_fleet_status_ticket_readiness_arch001.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/telemetry.py
  reason: 'Re-measured against the current floor rather than trusting the carried-forward
    claim list (T-2322 has since split _land_cmd.py''s ARCH functions, exactly the
    file T-2341''s original scope leaned on most).


    Resolved, removing their files from scope: all 5 ARCH001 (telemetry.py:189, _land_cmd.py:1969/2995/3443,
    _new.py:474), 2 of 3 ARCH103 (_land_cmd.py:3515/3599), DOC001 (docs/commands/release.md),
    both PERF004 (_land_cmd.py:3494, _new.py:984). None of these identities reproduce
    on the current floor -- verified via frob check --only archgate/docanchor/perf
    against unmodified main.


    Removing: src/frob/app/telemetry.py, src/frob/app/ticket_runner/_land_cmd.py,
    src/frob/app/ticket_runner/_new.py, docs/commands/release.md.


    Still live and fixed in this pass: ARCH103 fleet_status.py:1549 (split via _rot_bucket_lines),
    COV001 x5 (fleet_status.py VERIFY_QUEUE/VERIFY_WATERMARK/verify_queue_state, _land_git_ops.py::detect_duplicate_ticket_id_collisions,
    _quarantine.py::clear_quarantine), DOC002 x3 (same fleet_status.py/verify_runner.py
    anchor fixes).


    Still live, NOT fixed here, split into their own dispatches (children filed):
    COV003 x4 (T-1205/T-1235/T-1397/T-1526 evidence repair), TICK004 (tickets.md ledger-consistency
    investigation, 9 errors + 17 warnings under one identity).


    Still live, remaining in this ticket''s own scope for a follow-up pass: SELFAUDIT001
    (design, now 9 findings not 21 -- ratchet-based, drifts run to run) and WIRE003
    (docs/modules/cli.md ''path'' verb).

    '
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'Re-measured against the current floor rather than trusting the carried-forward
    claim list (T-2322 has since split _land_cmd.py''s ARCH functions, exactly the
    file T-2341''s original scope leaned on most).


    Resolved, removing their files from scope: all 5 ARCH001 (telemetry.py:189, _land_cmd.py:1969/2995/3443,
    _new.py:474), 2 of 3 ARCH103 (_land_cmd.py:3515/3599), DOC001 (docs/commands/release.md),
    both PERF004 (_land_cmd.py:3494, _new.py:984). None of these identities reproduce
    on the current floor -- verified via frob check --only archgate/docanchor/perf
    against unmodified main.


    Removing: src/frob/app/telemetry.py, src/frob/app/ticket_runner/_land_cmd.py,
    src/frob/app/ticket_runner/_new.py, docs/commands/release.md.


    Still live and fixed in this pass: ARCH103 fleet_status.py:1549 (split via _rot_bucket_lines),
    COV001 x5 (fleet_status.py VERIFY_QUEUE/VERIFY_WATERMARK/verify_queue_state, _land_git_ops.py::detect_duplicate_ticket_id_collisions,
    _quarantine.py::clear_quarantine), DOC002 x3 (same fleet_status.py/verify_runner.py
    anchor fixes).


    Still live, NOT fixed here, split into their own dispatches (children filed):
    COV003 x4 (T-1205/T-1235/T-1397/T-1526 evidence repair), TICK004 (tickets.md ledger-consistency
    investigation, 9 errors + 17 warnings under one identity).


    Still live, remaining in this ticket''s own scope for a follow-up pass: SELFAUDIT001
    (design, now 9 findings not 21 -- ratchet-based, drifts run to run) and WIRE003
    (docs/modules/cli.md ''path'' verb).

    '
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/ticket_runner/_new.py
  reason: 'Re-measured against the current floor rather than trusting the carried-forward
    claim list (T-2322 has since split _land_cmd.py''s ARCH functions, exactly the
    file T-2341''s original scope leaned on most).


    Resolved, removing their files from scope: all 5 ARCH001 (telemetry.py:189, _land_cmd.py:1969/2995/3443,
    _new.py:474), 2 of 3 ARCH103 (_land_cmd.py:3515/3599), DOC001 (docs/commands/release.md),
    both PERF004 (_land_cmd.py:3494, _new.py:984). None of these identities reproduce
    on the current floor -- verified via frob check --only archgate/docanchor/perf
    against unmodified main.


    Removing: src/frob/app/telemetry.py, src/frob/app/ticket_runner/_land_cmd.py,
    src/frob/app/ticket_runner/_new.py, docs/commands/release.md.


    Still live and fixed in this pass: ARCH103 fleet_status.py:1549 (split via _rot_bucket_lines),
    COV001 x5 (fleet_status.py VERIFY_QUEUE/VERIFY_WATERMARK/verify_queue_state, _land_git_ops.py::detect_duplicate_ticket_id_collisions,
    _quarantine.py::clear_quarantine), DOC002 x3 (same fleet_status.py/verify_runner.py
    anchor fixes).


    Still live, NOT fixed here, split into their own dispatches (children filed):
    COV003 x4 (T-1205/T-1235/T-1397/T-1526 evidence repair), TICK004 (tickets.md ledger-consistency
    investigation, 9 errors + 17 warnings under one identity).


    Still live, remaining in this ticket''s own scope for a follow-up pass: SELFAUDIT001
    (design, now 9 findings not 21 -- ratchet-based, drifts run to run) and WIRE003
    (docs/modules/cli.md ''path'' verb).

    '
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: docs/commands/release.md
  reason: 'Re-measured against the current floor rather than trusting the carried-forward
    claim list (T-2322 has since split _land_cmd.py''s ARCH functions, exactly the
    file T-2341''s original scope leaned on most).


    Resolved, removing their files from scope: all 5 ARCH001 (telemetry.py:189, _land_cmd.py:1969/2995/3443,
    _new.py:474), 2 of 3 ARCH103 (_land_cmd.py:3515/3599), DOC001 (docs/commands/release.md),
    both PERF004 (_land_cmd.py:3494, _new.py:984). None of these identities reproduce
    on the current floor -- verified via frob check --only archgate/docanchor/perf
    against unmodified main.


    Removing: src/frob/app/telemetry.py, src/frob/app/ticket_runner/_land_cmd.py,
    src/frob/app/ticket_runner/_new.py, docs/commands/release.md.


    Still live and fixed in this pass: ARCH103 fleet_status.py:1549 (split via _rot_bucket_lines),
    COV001 x5 (fleet_status.py VERIFY_QUEUE/VERIFY_WATERMARK/verify_queue_state, _land_git_ops.py::detect_duplicate_ticket_id_collisions,
    _quarantine.py::clear_quarantine), DOC002 x3 (same fleet_status.py/verify_runner.py
    anchor fixes).


    Still live, NOT fixed here, split into their own dispatches (children filed):
    COV003 x4 (T-1205/T-1235/T-1397/T-1526 evidence repair), TICK004 (tickets.md ledger-consistency
    investigation, 9 errors + 17 warnings under one identity).


    Still live, remaining in this ticket''s own scope for a follow-up pass: SELFAUDIT001
    (design, now 9 findings not 21 -- ratchet-based, drifts run to run) and WIRE003
    (docs/modules/cli.md ''path'' verb).

    '
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets/T-1205
  reason: 'Re-measured against the current floor rather than trusting the carried-forward
    claim list (T-2322 has since split _land_cmd.py''s ARCH functions, exactly the
    file T-2341''s original scope leaned on most).


    Resolved, removing their files from scope: all 5 ARCH001 (telemetry.py:189, _land_cmd.py:1969/2995/3443,
    _new.py:474), 2 of 3 ARCH103 (_land_cmd.py:3515/3599), DOC001 (docs/commands/release.md),
    both PERF004 (_land_cmd.py:3494, _new.py:984). None of these identities reproduce
    on the current floor -- verified via frob check --only archgate/docanchor/perf
    against unmodified main.


    Removing: src/frob/app/telemetry.py, src/frob/app/ticket_runner/_land_cmd.py,
    src/frob/app/ticket_runner/_new.py, docs/commands/release.md.


    Still live and fixed in this pass: ARCH103 fleet_status.py:1549 (split via _rot_bucket_lines),
    COV001 x5 (fleet_status.py VERIFY_QUEUE/VERIFY_WATERMARK/verify_queue_state, _land_git_ops.py::detect_duplicate_ticket_id_collisions,
    _quarantine.py::clear_quarantine), DOC002 x3 (same fleet_status.py/verify_runner.py
    anchor fixes).


    Still live, NOT fixed here, split into their own dispatches (children filed):
    COV003 x4 (T-1205/T-1235/T-1397/T-1526 evidence repair), TICK004 (tickets.md ledger-consistency
    investigation, 9 errors + 17 warnings under one identity).


    Still live, remaining in this ticket''s own scope for a follow-up pass: SELFAUDIT001
    (design, now 9 findings not 21 -- ratchet-based, drifts run to run) and WIRE003
    (docs/modules/cli.md ''path'' verb).

    '
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets/T-1235
  reason: 'Re-measured against the current floor rather than trusting the carried-forward
    claim list (T-2322 has since split _land_cmd.py''s ARCH functions, exactly the
    file T-2341''s original scope leaned on most).


    Resolved, removing their files from scope: all 5 ARCH001 (telemetry.py:189, _land_cmd.py:1969/2995/3443,
    _new.py:474), 2 of 3 ARCH103 (_land_cmd.py:3515/3599), DOC001 (docs/commands/release.md),
    both PERF004 (_land_cmd.py:3494, _new.py:984). None of these identities reproduce
    on the current floor -- verified via frob check --only archgate/docanchor/perf
    against unmodified main.


    Removing: src/frob/app/telemetry.py, src/frob/app/ticket_runner/_land_cmd.py,
    src/frob/app/ticket_runner/_new.py, docs/commands/release.md.


    Still live and fixed in this pass: ARCH103 fleet_status.py:1549 (split via _rot_bucket_lines),
    COV001 x5 (fleet_status.py VERIFY_QUEUE/VERIFY_WATERMARK/verify_queue_state, _land_git_ops.py::detect_duplicate_ticket_id_collisions,
    _quarantine.py::clear_quarantine), DOC002 x3 (same fleet_status.py/verify_runner.py
    anchor fixes).


    Still live, NOT fixed here, split into their own dispatches (children filed):
    COV003 x4 (T-1205/T-1235/T-1397/T-1526 evidence repair), TICK004 (tickets.md ledger-consistency
    investigation, 9 errors + 17 warnings under one identity).


    Still live, remaining in this ticket''s own scope for a follow-up pass: SELFAUDIT001
    (design, now 9 findings not 21 -- ratchet-based, drifts run to run) and WIRE003
    (docs/modules/cli.md ''path'' verb).

    '
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets/T-1397
  reason: 'Re-measured against the current floor rather than trusting the carried-forward
    claim list (T-2322 has since split _land_cmd.py''s ARCH functions, exactly the
    file T-2341''s original scope leaned on most).


    Resolved, removing their files from scope: all 5 ARCH001 (telemetry.py:189, _land_cmd.py:1969/2995/3443,
    _new.py:474), 2 of 3 ARCH103 (_land_cmd.py:3515/3599), DOC001 (docs/commands/release.md),
    both PERF004 (_land_cmd.py:3494, _new.py:984). None of these identities reproduce
    on the current floor -- verified via frob check --only archgate/docanchor/perf
    against unmodified main.


    Removing: src/frob/app/telemetry.py, src/frob/app/ticket_runner/_land_cmd.py,
    src/frob/app/ticket_runner/_new.py, docs/commands/release.md.


    Still live and fixed in this pass: ARCH103 fleet_status.py:1549 (split via _rot_bucket_lines),
    COV001 x5 (fleet_status.py VERIFY_QUEUE/VERIFY_WATERMARK/verify_queue_state, _land_git_ops.py::detect_duplicate_ticket_id_collisions,
    _quarantine.py::clear_quarantine), DOC002 x3 (same fleet_status.py/verify_runner.py
    anchor fixes).


    Still live, NOT fixed here, split into their own dispatches (children filed):
    COV003 x4 (T-1205/T-1235/T-1397/T-1526 evidence repair), TICK004 (tickets.md ledger-consistency
    investigation, 9 errors + 17 warnings under one identity).


    Still live, remaining in this ticket''s own scope for a follow-up pass: SELFAUDIT001
    (design, now 9 findings not 21 -- ratchet-based, drifts run to run) and WIRE003
    (docs/modules/cli.md ''path'' verb).

    '
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets/T-1526
  reason: 'Re-measured against the current floor rather than trusting the carried-forward
    claim list (T-2322 has since split _land_cmd.py''s ARCH functions, exactly the
    file T-2341''s original scope leaned on most).


    Resolved, removing their files from scope: all 5 ARCH001 (telemetry.py:189, _land_cmd.py:1969/2995/3443,
    _new.py:474), 2 of 3 ARCH103 (_land_cmd.py:3515/3599), DOC001 (docs/commands/release.md),
    both PERF004 (_land_cmd.py:3494, _new.py:984). None of these identities reproduce
    on the current floor -- verified via frob check --only archgate/docanchor/perf
    against unmodified main.


    Removing: src/frob/app/telemetry.py, src/frob/app/ticket_runner/_land_cmd.py,
    src/frob/app/ticket_runner/_new.py, docs/commands/release.md.


    Still live and fixed in this pass: ARCH103 fleet_status.py:1549 (split via _rot_bucket_lines),
    COV001 x5 (fleet_status.py VERIFY_QUEUE/VERIFY_WATERMARK/verify_queue_state, _land_git_ops.py::detect_duplicate_ticket_id_collisions,
    _quarantine.py::clear_quarantine), DOC002 x3 (same fleet_status.py/verify_runner.py
    anchor fixes).


    Still live, NOT fixed here, split into their own dispatches (children filed):
    COV003 x4 (T-1205/T-1235/T-1397/T-1526 evidence repair), TICK004 (tickets.md ledger-consistency
    investigation, 9 errors + 17 warnings under one identity).


    Still live, remaining in this ticket''s own scope for a follow-up pass: SELFAUDIT001
    (design, now 9 findings not 21 -- ratchet-based, drifts run to run) and WIRE003
    (docs/modules/cli.md ''path'' verb).

    '
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: needed to add the detect_duplicate_ticket_id_collisions doc section fixing
    its COV001/DOC002 findings
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_coordinator_scripts.py::TestVerifyQueueState::test_reports_depth_and_oldest_age
- tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_refuses_when_not_raised
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides
- tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Re-measurement of T-2331 (post-land sweep regression from T-2299, filed
2026-08-17 20:27) against the CURRENT floor (2026-08-17, post T-2290/
T-2310/T-2317/T-2324 watermark fix): 27 of the 32 claimed (rule, file)
identities genuinely reproduce; 5 are stale (see T-2331's Done report for
the full method and the stale list). Of the 27 real ones, 8 are already
attributed by the sweep's own reachability analysis to OTHER, already-
closed/dropped tickets (T-2242, T-2310, T-2298, T-2178) -- those are
folded into those tickets' own residue, not this one.

This ticket tracks the remaining 19 genuinely-new, UNATTRIBUTED identities
that need real code changes, not a quick fix -- several are architecture-
complexity gates (ARCH001/ARCH103) that require restructuring function
bodies, not a one-line change:

ARCH001 (extract-or-simplify, function too entangled):
- src/frob/app/telemetry.py:189
- src/frob/app/ticket_runner/_land_cmd.py:1969,2995,3443 (3 sites)
- src/frob/app/ticket_runner/_new.py:474

ARCH103 (mixes I/O + string-formatting + branching in one body):
- scripts/fleet_status.py:1549
- src/frob/app/ticket_runner/_land_cmd.py:3515,3599

COV001 (missing frob:tests edge on a touched public symbol):
- scripts/fleet_status.py:119,120,1686
- src/frob/tickets/_land_git_ops.py:1199
- src/frob/verify/_quarantine.py:471

COV003 (ticket file missing required coverage/evidence linkage):
- tickets/T-1205
- tickets/T-1235
- tickets/T-1397
- tickets/T-1526

DOC001 (broken/missing doc anchor):
- docs/commands/release.md

DOC002 (missing frob:doc edge on a touched public symbol):
- scripts/fleet_status.py:1675,1960
- src/frob/app/verify_runner.py:268

PERF004 (missing/stale perf directive):
- src/frob/app/ticket_runner/_land_cmd.py:3494
- src/frob/app/ticket_runner/_new.py:984

SELFAUDIT001 (design self-audit, 21 findings under a single `design`
identity -- needs its own investigation into what design/frob.strata
content is drifting):
- design (21 findings, `frob check --only sys` for detail)

TICK004 (ledger-consistency, 9 errors + 17 warnings under one identity):
- tickets.md

WIRE003 (wiring/reachability gap):
- docs/modules/cli.md

Plan: triage each rule family separately -- ARCH001/ARCH103 need actual
refactoring of the named functions (extract helpers, reduce branching);
COV001/COV002/DOC001/DOC002 need frob:tests/frob:doc directives added at
the named symbols; COV003 needs the four named tickets' evidence/coverage
brought into compliance with whatever COV003 currently demands; TICK004
and SELFAUDIT001 need their own read of `frob check --only tickets --only
sys` output to see the full finding text before deciding a fix, since both
collapse many findings into one (rule, file) identity here.

Do NOT force a quick fix through ARCH001/ARCH103 -- these are architecture
gates that reward a genuine decomposition, not a suppression. If a finding
turns out to be a false positive on inspection, waive it with a specific
reason (frob:waive RULE reason="..."), never blanket.

frob:no-behavior-change reason="every change in this pass is a pure structural/documentation fix, not a runtime defect repair: the ARCH103 split (_rot_bucket_lines extracted from _print_rot_bucket) preserves identical output, verified by the existing tests/system/test_fleet_status_ticket_readiness_arch001.py and tests/unit/test_coordinator_scripts.py -k Rot (11 tests) passing unmodified; every other change is a frob:doc edge or doc-anchor-slug correction with zero runtime effect. There is no user-facing defect for this ticket's own bound evidence to reproduce -- COV001/DOC002/ARCH103 are gate-coverage findings, not behavior bugs."