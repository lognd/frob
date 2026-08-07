---
id: T-1195
title: 'arch: 33-file LARGE001 residue after T-1192 split (_new_renumber.py done)'
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
- docs/modules/arch.md
- tests/test_arch_near_duplicate_native.py
- tests/unit/test_arch.py
- tests/unit/test_check_budget.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/arch.md
  reason: split arch/_python.py's abstraction-opportunity family into arch/_abstraction.py;
    carried doc prose + test imports/directives to new module path
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_arch_near_duplicate_native.py
  reason: split arch/_python.py's abstraction-opportunity family into arch/_abstraction.py;
    carried doc prose + test imports/directives to new module path
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/unit/test_arch.py
  reason: split arch/_python.py's abstraction-opportunity family into arch/_abstraction.py;
    carried doc prose + test imports/directives to new module path
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/unit/test_check_budget.py
  reason: moved chunked-check bookkeeping tests reference new _check_chunking module
    directly
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_dispatch_family_no_abstraction_opportunity
- tests/test_arch_near_duplicate_native.py::test_near_duplicate_cluster_dispatches_to_native_and_matches_reference
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_mode_calls_stamp_and_returns
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_runs_selected_chunks_and_reports_result
- tests/unit/test_arch.py::TestLanguageParityExclusion::test_non_parity_group_still_flagged[duplicate_rust_tag]
designated_repro_test: null
threat: null
component: null
---
## Description

T-1192 split ONE file off its 34-file LARGE001 residue list this land
(src/frob/tickets/_new_renumber.py: 847 -> 691 lines, moving
finalize_draft/finalize_draft_for_land into a new
src/frob/tickets/_draft_finalize.py). Budget did not allow the other 33.

Still unowned, current line counts as of T-1192's own filing (re-measure
before starting -- some may have shifted from unrelated work landing in
between):

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
- src/frob/vet/_capability.py (5944) -- T-1074 explicitly flagged this
  and the next file as needing a dedicated follow-up but did not file
  one ("budget did not allow investigating a safe split boundary for
  either").
- src/frob/vet/_capability_registry.py (2918)
- src/frob/vet/_scan.py (901)

(src/frob/tickets/_new_renumber.py dropped off this list -- T-1192
brought it under the 800-line threshold.)

## Plan

Same discipline as T-1072/T-1074/T-1186/T-1187/T-1188/T-1189/T-1192: pick
a cohesive subsystem slice per land, split it (or record an
accepted-with-reason disposition per T-1074's precedent if no safe seam
exists), full verification per group, re-measure, re-file remaining
residue rather than closing silently. LARGE001 is a warning-tier,
waivable advisory (`frob:waive LARGE001 reason="..."`, file-level since a
file-level finding has no symref) -- not every file on this list needs a
structural split; a disposition is a valid, honest outcome where a real
split boundary would fragment a genuinely cohesive module (T-1074's own
precedent for the 7 files it dispositioned rather than split).