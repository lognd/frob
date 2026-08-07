---
id: T-1146
title: 'strata: wire check_resource_contention''s module= param into SELFAUDIT001/sys_runner,
  drop tickets_ledger SYS203 waivers'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/app/sys_runner.py
- src/frob/strata/_design_load.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_mode_conformance_violation
- tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_arbitered_store_discharges
designated_repro_test: null
threat: null
component: null
---
T-1025 taught check_resource_contention/_shared_store_write_violations
(src/frob/strata/_contention.py) an optional `module: Module | None`
parameter: when a store id is also a `resource` id declaring
`arbitrated_by`/`lock`, its SYS203 shared-store-write finding is now
skipped entirely (the same discharge condition SYS204's
resource_contention_violations already applies).

This is fully built and tested in isolation, but NOT yet wired into
either live caller:
- src/frob/gates/__init__.py's SELFAUDIT001 gate (the `frob check --only
  sys` stage) calls check_resource_contention(model,
  store_ids=design_ids.store_ids) with no `module=` argument.
- src/frob/app/sys_runner.py's `frob sys audit` CLI report does the same.

Neither caller has an in-scope way to source a `module` today:
src/frob/strata/_design_load.py's DesignIds dataclass carries only
elaborated KernelModels (`models`) and a merged store-id set
(`store_ids`), never the raw pre-elaboration `Module` objects (or their
`.resources`) needed to look up an arbiter.

To close the loop and let the five `SYS203:tickets_ledger` waivers in
design/frob.strata finally be dropped (T-1025's own stated goal), this
follow-up needs:
1. DesignIds (or a new sibling field) to also carry the merged
   `Module.resources` (or the raw parsed Modules) alongside `store_ids`.
2. gates/__init__.py's SELFAUDIT001 call site and sys_runner.py's `frob
   sys audit` call site both updated to pass `module=` (or an
   equivalent merged-resources argument) through to
   check_resource_contention.
3. Verify `frob check --only sys` stays green with the five
   `SYS203:tickets_ledger` waivers REMOVED from design/frob.strata (the
   arbiter should now discharge them for real, not via the waiver).

Filed rather than done inline because gates/__init__.py is contested
turf this wave (a sibling gates-family-splitter ticket holds much of it)
and _design_load.py/sys_runner.py wiring was outside T-1025's own
declared scope.