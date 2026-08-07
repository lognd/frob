---
id: T-1270
title: 'arch: 32-file LARGE001 residue after T-1195 split'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/_ticket.py
- src/frob/app/config.py
- src/frob/app/sys_runner.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/arch/_patterns.py
- src/frob/check/__init__.py
- src/frob/check/_python.py
- src/frob/doctor.py
- src/frob/gates/_docptr.py
- src/frob/gates/_protocol_summary.py
- src/frob/gates/_registry_exhaustiveness.py
- src/frob/gates/_secrets.py
- src/frob/gates/_tickets_gate.py
- src/frob/gates/_waive.py
- src/frob/strata/__init__.py
- src/frob/strata/_audit.py
- src/frob/strata/_compliance.py
- src/frob/strata/_elaborate.py
- src/frob/strata/_host_isolation.py
- src/frob/strata/_infra.py
- src/frob/strata/_mode_conformance.py
- src/frob/strata/_selfconform.py
- src/frob/strata/_threat.py
- src/frob/tickets/_evidence.py
- src/frob/tickets/_land.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_models.py
- src/frob/vet/_capability.py
- src/frob/vet/_capability_registry.py
- src/frob/vet/_scan.py
- src/frob/arch/_python.py
- src/frob/app/check_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/_cli_parsers/_ticket.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/config.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/arch/_patterns.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/check/__init__.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/check/_python.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/doctor.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gates/_docptr.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gates/_protocol_summary.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gates/_registry_exhaustiveness.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gates/_secrets.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gates/_waive.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/__init__.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_audit.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_compliance.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_elaborate.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_host_isolation.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_infra.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_mode_conformance.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_threat.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/tickets/_land.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/tickets/_models.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/vet/_capability.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/vet/_capability_registry.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/vet/_scan.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/arch/_python.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/check_runner.py
  reason: narrow from broad src/frob/ catch-all to the specific residue files this
    ticket tracks -- avoids ambiguous-scope ties with other open tickets' scope-coverage
    claims (COV002 B10)
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/test_config.py::test_reads_override
- tests/unit/test_config.py::test_missing_toml_defaults
- tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch
- tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_reads_and_merges_tool_frob_table
- tests/unit/test_app_config_from_external_t1276.py::TestFromArgs::test_delegates_to_from_external_with_pyproject_default
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_new_list_doable
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_with_evidence_and_done_report_succeeds
- tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130
- tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy::test_healthy_plain_prints_all_available_and_does_not_exit
designated_repro_test: null
threat: null
component: null
---
T-1195 split 3 files this land (arch/_python.py, app/check_runner.py,
gates/_docblocks.py). Budget did not allow the other 30.

Still unowned, current line counts as of T-1195's own filing (re-measure
before starting -- some may have shifted from unrelated work landing in
between):

- src/frob/_cli_parsers/_ticket.py (1102)
- src/frob/app/config.py (1167)
- src/frob/app/sys_runner.py (1023)
- src/frob/app/ticket_runner/_land_cmd.py (907)
- src/frob/app/ticket_runner/_verify.py (973)
- src/frob/arch/_patterns.py (1486)
- src/frob/check/__init__.py (953)
- src/frob/check/_python.py (977)
- src/frob/doctor.py (918)
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
- src/frob/tickets/_evidence.py (1201)
- src/frob/tickets/_land.py (1178)
- src/frob/tickets/_leases.py (1339)
- src/frob/tickets/_models.py (1873)
- src/frob/vet/_capability.py (5944) -- T-1074 explicitly flagged this
  and the next file as needing a dedicated follow-up but did not file
  one ("budget did not allow investigating a safe split boundary for
  either").
- src/frob/vet/_capability_registry.py (2918)
- src/frob/vet/_scan.py (901)

Also newly grown over threshold this land (not previously on any
residue list -- picked up incidentally while re-measuring):

- src/frob/arch/_python.py (962, post-T-1195 split; still over 800)
- src/frob/app/check_runner.py (1127, post-T-1195 split; still over 800)

## Plan

Same discipline as T-1072/T-1074/T-1186/T-1187/T-1188/T-1189/T-1192/
T-1195: pick a cohesive subsystem slice per land, split it (or record an
accepted-with-reason disposition per T-1074's precedent if no safe seam
exists), full verification per group, re-measure, re-file remaining
residue rather than closing silently. LARGE001 is a warning-tier,
waivable advisory (`frob:waive LARGE001 reason="..."`, file-level since a
file-level finding has no symref) -- not every file on this list needs a
structural split; a disposition is a valid, honest outcome where a real
split boundary would fragment a genuinely cohesive module (T-1074's own
precedent for the 7 files it dispositioned rather than split).