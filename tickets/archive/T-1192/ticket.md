---
id: T-1192
title: 'arch: large-file residue after T-1074/T-1186/T-1187 splits (34 unowned LARGE001
  findings)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
- tests/test_tickets_collision.py
- docs/modules/tickets.md
- tests/test_tickets_ledger_concurrency.py
- src/frob/gates/_fix_engine.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_collision.py
  reason: finalize_draft/finalize_draft_for_land moved to _draft_finalize.py; these
    test/doc files carry frob:tests/frob:describes directives naming the old file
    path
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/tickets.md
  reason: finalize_draft/finalize_draft_for_land moved to _draft_finalize.py; these
    test/doc files carry frob:tests/frob:describes directives naming the old file
    path
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_tickets_ledger_concurrency.py
  reason: finalize_draft/finalize_draft_for_land moved to _draft_finalize.py; these
    test/doc files carry frob:tests/frob:describes directives naming the old file
    path
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: finalize_draft moved out of _new_renumber.py into _draft_finalize.py; _fix_engine.py's
    deferred import needs repointing
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/gates.md
  reason: fix_tick002_renumber's doc description named the old _new_renumber.finalize_draft
    import path; updated to _draft_finalize
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_tickets_collision.py::TestRenumberRewritesLedgerProse::test_finalize_draft_rewrites_a_sibling_ticket_done_report_prose
- tests/test_tickets_collision.py::TestFinalizeDraftForLandMainFreshCeiling::test_id_ceiling_reads_current_main_not_stale_worktree_view
- tests/test_tickets_ledger_concurrency.py::TestFinalizeDraftAllocationRace::test_two_concurrent_finalize_draft_calls_get_distinct_ids
designated_repro_test: null
threat: null
component: null
---
T-0395 verification close (2026-07-29) re-measured LARGE001 (`frob check
--only archgate`, calibrated 800-line threshold) and found this genuinely
unowned residue after excluding: native crates (frob-core/src/lib.rs,
strata-core/src/lib.rs, strata-core/src/parse/mod.rs -- separate
toolchain/ownership per the T-1074 precedent), the two currently-live
split tickets (T-1188 owns src/frob/gates/__init__.py, T-1189 owns
src/frob/tickets/_land_merge.py + _land_finalize.py), and the 7 files
T-1074 already recorded an explicit accepted-with-reason disposition for
(src/frob/arch/_rust.py, src/frob/dup/_pipeline/_fingerprint.py,
src/frob/graph/__init__.py, src/frob/graph/callgraph.py,
src/frob/graph/dsl.py, src/frob/perf/_effect_summaries.py,
src/frob/perf/_rules.py).

Remaining genuinely unowned LARGE001 findings (current line counts):
- src/frob/_cli_parsers/_ticket.py (1102)
- src/frob/app/check_runner.py (1597)
- src/frob/app/config.py (1167)
- src/frob/app/sys_runner.py (1023)
- src/frob/app/ticket_runner/_land_cmd.py (907)
- src/frob/app/ticket_runner/_verify.py (973)
- src/frob/arch/_patterns.py (1486)
- src/frob/arch/_python.py (1635)
- src/frob/check/__init__.py (953)
- src/frob/check/_python.py (977)
- src/frob/doctor.py (918)
- src/frob/gates/_docblocks.py (1465)
- src/frob/gates/_docptr.py (1000)
- src/frob/gates/_protocol_summary.py (1244)
- src/frob/gates/_registry_exhaustiveness.py (988)
- src/frob/gates/_secrets.py (1088)
- src/frob/gates/_tickets_gate.py (953)
- src/frob/gates/_waive.py (1424)
- src/frob/strata/__init__.py (941)
- src/frob/strata/_audit.py (1055)
- src/frob/strata/_compliance.py (1058)
- src/frob/strata/_elaborate.py (1401)
- src/frob/strata/_host_isolation.py (1281)
- src/frob/strata/_infra.py (837)
- src/frob/strata/_mode_conformance.py (867)
- src/frob/strata/_selfconform.py (1621)
- src/frob/strata/_threat.py (2485)
- src/frob/tickets/_evidence.py (1201) -- its prior owner T-1171 is done;
  the exclusion no longer applies.
- src/frob/tickets/_land.py (1178) -- T-1186's own split left this file
  itself still over threshold; not in T-1189's scope (which covers only
  the two NEW files T-1186 produced), so it is unowned residue too.
- src/frob/tickets/_leases.py (1339)
- src/frob/tickets/_models.py (1873)
- src/frob/tickets/_new_renumber.py (840)
- src/frob/vet/_capability.py (5944) -- T-1074 explicitly flagged this
  and the next file as needing a dedicated follow-up but did not file
  one ("budget did not allow investigating a safe split boundary for
  either") -- filing it now.
- src/frob/vet/_capability_registry.py (2918)
- src/frob/vet/_scan.py (901)

LARGE001 is a warning-tier, unwaivable advisory (per docs/modules/
gates.md) -- none of this blocks a gate today, but per T-0395/T-1074's
own framing it needs real splits or a recorded per-file accepted-with-
reason disposition, triaged in groups (one subsystem per land, full
verification per group), not one giant diff. Same discipline as
T-1072/T-1074/T-1186/T-1187/T-1188/T-1189: pick a cohesive subsystem
slice, split it, re-measure, re-file remaining residue rather than
closing silently.