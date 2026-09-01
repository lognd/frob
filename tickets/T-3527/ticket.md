---
id: T-3527
title: implement growth-rate grammar for frob sys capacity --at DATE
state: done
kind: feature
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/strata/kernel.md
- docs/strata/reliability.md
- src/frob/strata/_capacity.py
- strata-core/src/parse/**
- src/frob/strata/_design_load.py
- src/frob/strata/_ast.py
- src/frob/strata/_elaborate.py
- src/frob/strata/_models.py
- src/frob/strata/_facts.py
- src/frob/app/sys_runner.py
- src/frob/app/config.py
- src/frob/app/_cli_parsers/_misc.py
- docs/commands/sys.md
- src/frob/_cli_parsers/_misc.py
- src/frob/strata/_infra.py
- src/frob/strata/__init__.py
- src/frob/app/_config_external.py
- docs/strata/surface.md
- tests/unit/strata/test_demand.py
- tests/unit/strata/test_capacity_projection.py
- tests/unit/test_app_sys_capacity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/parse/**
  reason: Series DD measured the fix requires the Rust parser (strata_core.parse_source
    is the sole AST source); widened so the ticket is workable as filed
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/strata/_design_load.py
  reason: Series DD measured the fix requires the Rust parser (strata_core.parse_source
    is the sole AST source); widened so the ticket is workable as filed
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/strata/_ast.py
  reason: 'Fail-log attempt 2 enumerated exactly these: growth-rate grammar is a shared-kernel-primitive
    change touching NodeDecl AST, elaboration, Node models, aggregate_demand seeding,
    plus --since/--at CLI wiring; parser-side widening (Series DD) was necessary but
    not sufficient'
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/strata/_elaborate.py
  reason: 'Fail-log attempt 2 enumerated exactly these: growth-rate grammar is a shared-kernel-primitive
    change touching NodeDecl AST, elaboration, Node models, aggregate_demand seeding,
    plus --since/--at CLI wiring; parser-side widening (Series DD) was necessary but
    not sufficient'
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/strata/_models.py
  reason: 'Fail-log attempt 2 enumerated exactly these: growth-rate grammar is a shared-kernel-primitive
    change touching NodeDecl AST, elaboration, Node models, aggregate_demand seeding,
    plus --since/--at CLI wiring; parser-side widening (Series DD) was necessary but
    not sufficient'
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/strata/_facts.py
  reason: 'Fail-log attempt 2 enumerated exactly these: growth-rate grammar is a shared-kernel-primitive
    change touching NodeDecl AST, elaboration, Node models, aggregate_demand seeding,
    plus --since/--at CLI wiring; parser-side widening (Series DD) was necessary but
    not sufficient'
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: 'Fail-log attempt 2 enumerated exactly these: growth-rate grammar is a shared-kernel-primitive
    change touching NodeDecl AST, elaboration, Node models, aggregate_demand seeding,
    plus --since/--at CLI wiring; parser-side widening (Series DD) was necessary but
    not sufficient'
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/app/config.py
  reason: 'Fail-log attempt 2 enumerated exactly these: growth-rate grammar is a shared-kernel-primitive
    change touching NodeDecl AST, elaboration, Node models, aggregate_demand seeding,
    plus --since/--at CLI wiring; parser-side widening (Series DD) was necessary but
    not sufficient'
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/app/_cli_parsers/_misc.py
  reason: 'Fail-log attempt 2 enumerated exactly these: growth-rate grammar is a shared-kernel-primitive
    change touching NodeDecl AST, elaboration, Node models, aggregate_demand seeding,
    plus --since/--at CLI wiring; parser-side widening (Series DD) was necessary but
    not sufficient'
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/commands/sys.md
  reason: 'scope closure: sys_runner.py frob:doc targets live here; --at DATE CLI
    change must update its doc in the same land'
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: declared glob src/frob/app/_cli_parsers/_misc.py does not exist; the real
    --population/--at/--since CLI parser for sys capacity lives at src/frob/_cli_parsers/_misc.py
    (no app/ segment) -- adding the correct path rather than failing
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: declared glob src/frob/app/_cli_parsers/_misc.py does not exist; the real
    --population/--at/--since CLI parser for sys capacity lives at src/frob/_cli_parsers/_misc.py
    (no app/ segment) -- adding the correct path rather than failing
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/strata/_infra.py
  reason: StoreDecl -> Node elaboration lives in _infra.py::_elaborate_store, not
    _elaborate.py -- store-side growth wiring (T-0261 node/store users/rate symmetry,
    already exercised by the Rust grammar tests) needs this file to thread users_growth/rate_growth
    the same way node's does
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/strata/__init__.py
  reason: Growth (new _models.py public symbol) needs re-export through the package
    __init__ same as every other kernel model (Capacity, Quantity, ...) or it is unreachable
    to test/CLI code outside the strata package
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/app/_config_external.py
  reason: AppConfig.from_external's generic argv-to-model copy only forwards fields
    listed in per-type allowlists (_FLOAT_FIELDS etc); sys_capacity_since/sys_capacity_at
    are datetime fields with no existing group, so --since/--at parse correctly but
    are silently dropped (None) through real CLI wiring without this file -- exactly
    the T-1927 live-fire regression class _config_external.py's own tests already
    guard for --population
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/strata/surface.md
  reason: AFFECT001 needs surface.md#parser/#stdinfra updated for the new users_growth/rate_growth
    NodeDecl/StoreDecl fields; the other three globs are the test files I wrote/extended
    for this feature's coverage, flagged by SCOPE001
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tests/unit/strata/test_demand.py
  reason: AFFECT001 needs surface.md#parser/#stdinfra updated for the new users_growth/rate_growth
    NodeDecl/StoreDecl fields; the other three globs are the test files I wrote/extended
    for this feature's coverage, flagged by SCOPE001
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tests/unit/strata/test_capacity_projection.py
  reason: AFFECT001 needs surface.md#parser/#stdinfra updated for the new users_growth/rate_growth
    NodeDecl/StoreDecl fields; the other three globs are the test files I wrote/extended
    for this feature's coverage, flagged by SCOPE001
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tests/unit/test_app_sys_capacity.py
  reason: AFFECT001 needs surface.md#parser/#stdinfra updated for the new users_growth/rate_growth
    NodeDecl/StoreDecl fields; the other three globs are the test files I wrote/extended
    for this feature's coverage, flagged by SCOPE001
  actor: logan
  at: '2026-08-31'
evidence:
- tests/unit/strata/test_demand.py::TestAggregateDemandGrowth::test_growth_scales_seed_before_fan_in
- tests/unit/strata/test_demand.py::TestAggregateDemandGrowth::test_elapsed_seconds_none_reproduces_ungrown_value
- tests/unit/strata/test_demand.py::TestAggregateDemandGrowth::test_each_node_grows_by_its_own_independent_rate
- tests/unit/strata/test_demand.py::TestAggregateDemandGrowth::test_rate_growth_applies_independently_of_users_growth
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityGrowth::test_at_projects_growth_and_can_fire
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityGrowth::test_since_without_at_fails_closed
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityGrowth::test_at_without_since_fails_closed
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityGrowth::test_no_since_or_at_leaves_elapsed_seconds_none
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_at_date_reports_projected_elapsed
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_since_without_at_is_an_error
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_since_and_at_flags_survive_real_argv_parsing
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2016 (done) produced only the DESIGN for a growth-rate declaration on Node.users/rate (docs/strata/kernel.md#growth-rate-declarations-t-2016) -- the grammar itself was never implemented, so frob sys capacity --at DATE (docs/strata/reliability.md's own Disclosed scope cut section) remains not yet implemented with no ticket currently tracking the implementation. Found while reviewing NEGEXIST001 for T-3519 (a doc claim needs a real frob:until binding, and none existed). Build the growth-rate grammar per T-2016's design and wire --at DATE into project_capacity.

## Failure log
- 2026-08-31 attempt 1: Grammar parsing is Rust-side only: strata_core.parse_source (strata-core/src/parse/*.rs) is the sole source of NodeDecl fields -- no Python lexer/parser exists for users/rate clauses to extend. Adding 'growth PERCENT per PERIOD' requires modifying strata-core's Rust parser and rebuilding the native extension, outside this ticket's declared scope (docs/strata/kernel.md, docs/strata/reliability.md, src/frob/strata/_capacity.py only) -- a materially larger cross-boundary change than the scope grant covers, exactly the under-scoping risk the ticket body's own UNMISSABLE warning flags. Re-file with strata-core/src/parse/** in declared scope before attempting implementation.
- 2026-08-31 attempt 2: growth-rate grammar requires touching src/frob/strata/_ast.py (NodeDecl), _elaborate.py, _models.py (Node.users/rate growth fields), and _facts.py (aggregate_demand seed reordering) plus CLI wiring in src/frob/app/sys_runner.py, app/config.py, _cli_parsers/_misc.py for --since/--at -- none in T-3527's declared scope; the parser-side widening already done (Series DD) is necessary but not sufficient -- this is a shared-kernel-primitive change per the ticket's own UNMISSABLE note, not a leaf addition to _capacity.py