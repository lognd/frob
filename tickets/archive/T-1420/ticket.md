---
id: T-1420
title: 'arch: 51-file LARGE001 residue after T-1270''s 2-file split'
state: done
kind: feature
origin: agent
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/lib.rs
- strata-core/src/parse/mod.rs
- src/frob/tickets/_models.py
- src/frob/tickets/_store.py
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_reporting.py
- src/frob/tickets/_reporting_attachments.py
- src/frob/vet/_capability.py
- src/frob/vet/_scan.py
- src/frob/vet/_scan_violations.py
- strata-core/src/parse/**
- tests/test_capability_registry.py
- tests/test_vet.py
- tests/test_gates.py
- tests/test_tickets_collision.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability_registry.py
  reason: the file this split deletes; land's UnownedDeletions check does not treat
    the src/** glob as covering it, and the ledger splice dropped this entry when
    main was merged forward
  actor: logan
  at: '2026-08-02'
- op: remove
  glob: src/**
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_store.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_reporting_attachments.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/vet/_capability.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/vet/_scan.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/vet/_scan_violations.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: strata-core/src/lib.rs
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: strata-core/src/parse/**
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/**
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/**
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: remove
  glob: frob-core/src/lib.rs
  reason: neither file appears in the current unwaived LARGE001 finding set; drop
    from scope to keep the lease minimal (re-applying the same narrowing lost by the
    tickets.md main-restore step)
  actor: logan
  at: '2026-08-02'
- op: remove
  glob: src/frob/vet/_capability_registry.py
  reason: neither file appears in the current unwaived LARGE001 finding set; drop
    from scope to keep the lease minimal (re-applying the same narrowing lost by the
    tickets.md main-restore step)
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_capability_registry.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_vet.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_tickets_collision.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_matrix_covers_every_kind_and_language
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_operation_kind_and_language_registered
- tests/test_capability_registry.py::TestValidateRegistryKinds::test_known_kinds_pass
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_survives_a_foreign_install_copy
- tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_called_private_helper_is_not_flagged
- tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged
- tests/test_gates.py::TestWireGate::test_relocated_symbol_via_file_split_is_not_flagged
- tests/test_gates.py::TestSysGate::test_sys001_dangling
- tests/test_gates.py::TestSysGate::test_doc003_proved_claim_passes
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_compliance_violation
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
- tests/test_tickets_collision.py::TestRenumberOneV2::test_git_mv_renames_directory_and_rewrites_id_field
- tests/test_tickets_collision.py::TestRenumberOneV2::test_sibling_ticket_prose_citation_rewritten
- tests/test_tickets_collision.py::TestRenumberOneV2::test_dry_run_mutates_nothing
- tests/test_tickets_collision.py::TestRenumberOneV2::test_target_id_already_exists_is_duplicate_id
- tests/test_tickets_collision.py::TestRenumberOneV2::test_unknown_old_id_is_not_found
designated_repro_test: null
threat: null
component: null
---
T-1270 cleared 2 of the 32 files on its list this pass (src/frob/_cli_parsers/_ticket.py
split into a per-concern package; src/frob/app/config.py split by extracting its two
procedural blocks -- from_external's field-copy loop and the stale-install/arch-config
helpers -- into app/_config_external.py and app/_config_meta.py). Both splits verified
scoped-and-foreground (pytest on the covering test files, ruff/format clean) before
landing.

51 unwaived LARGE001 findings remain repo-wide as of this measurement (down from 53),
listed below with current line counts. Same instruction as T-1270's own brief: pick a
cohesive subsystem slice per land, split it where a real seam exists (a parser/renderer
split, a coherent helper family, a distinct concern), or record an accepted-with-reason
frob:waive LARGE001 where the file is a genuinely single irreducible unit -- do not
raise the threshold and do not waive merely for size.

- frob-core/src/lib.rs (2277)
- strata-core/src/lib.rs (869)
- strata-core/src/parse/mod.rs (1744)
- src/frob/app/check_runner.py (1267)
- src/frob/app/sys_runner.py (1023)
- src/frob/app/ticket_runner/_close_cmd.py (1086)
- src/frob/app/ticket_runner/_land_cmd.py (967)
- src/frob/app/ticket_runner/_verify.py (973)
- src/frob/arch/_patterns.py (1486)
- src/frob/arch/_python.py (962)
- src/frob/arch/_rust.py (838)
- src/frob/check/__init__.py (959)
- src/frob/check/_python.py (1063)
- src/frob/doctor.py (920)
- src/frob/dup/_pipeline/_fingerprint.py (812)
- src/frob/gates/__init__.py (6713)
- src/frob/gates/_coverage.py (916)
- src/frob/gates/_debt_deprecated.py (851)
- src/frob/gates/_docblocks.py (822)
- src/frob/gates/_docptr.py (1468)
- src/frob/gates/_fix_engine.py (1401)
- src/frob/gates/_protocol_summary.py (1244)
- src/frob/gates/_registry_exhaustiveness.py (988)
- src/frob/gates/_secrets.py (1089)
- src/frob/gates/_sys.py (818)
- src/frob/gates/_tickets_gate.py (1077)
- src/frob/gates/_waive.py (1459)
- src/frob/graph/__init__.py (864)
- src/frob/graph/callgraph.py (830)
- src/frob/graph/dsl.py (1075)
- src/frob/perf/_effect_summaries.py (823)
- src/frob/perf/_rules.py (840)
- src/frob/strata/__init__.py (957)
- src/frob/strata/_audit.py (1055)
- src/frob/strata/_compliance.py (1257)
- src/frob/strata/_elaborate.py (1403)
- src/frob/strata/_host_isolation.py (1285)
- src/frob/strata/_infra.py (837)
- src/frob/strata/_mode_conformance.py (871)
- src/frob/strata/_selfconform.py (1608)
- src/frob/strata/_threat.py (2522)
- src/frob/tickets/_evidence.py (1369)
- src/frob/tickets/_land.py (1831)
- src/frob/tickets/_land_squash.py (919)
- src/frob/tickets/_leases.py (1403)
- src/frob/tickets/_models.py (1917)
- src/frob/tickets/_new_renumber.py (963)
- src/frob/tickets/_store.py (1552)
- src/frob/vet/_capability.py (6020, T-1074-flagged, still no dedicated follow-up filed)
- src/frob/vet/_capability_registry.py (2991, same T-1074 flag)
- src/frob/vet/_scan.py (901)

Note: src/frob/tickets/ and src/frob/app/ticket_runner/ overlap T-1296's strata TEST005
lease and other concurrent tickets' scopes at filing time -- narrow scope via
`frob ticket scope` before starting, per playbook section 4/lease-collision guidance.