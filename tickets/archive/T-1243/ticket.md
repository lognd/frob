---
id: T-1243
title: 'tickets: cluster dispatch -- brief and lease an epic/story as one agent mission'
state: done
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/_ticket.py
- src/frob/tickets/_doable.py
- docs/modules/tickets.md
- tests/test_tickets_lease.py
- src/frob/tickets/_brief.py
- src/frob/tickets/_reporting.py
- src/frob/tickets/__init__.py
- src/frob/_cli_parsers/_ticket/_query.py
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/app/config.py
- tests/test_tickets_brief.py
- src/frob/app/_config_external.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
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
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/_ticket.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/tickets.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_tickets_lease.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_brief.py
  reason: 'Prior agent mapped the real surface for T-1243: frob.tickets._brief.compose_brief

    needs cluster-aware composition, frob.tickets._reporting.brief_ticket is the

    public entry point brief_ticket dispatches through, frob.tickets.__init__

    carries epic_rollup (descendant walk this ticket needs for dependency

    ordering), the CLI parsers for brief/start/work live in

    src/frob/_cli_parsers/_ticket/_query.py and _progress.py (not the

    _cli_parsers/_ticket.py monolith path named in the original scope, which was

    split by T-1270 before this ticket was filed), the dispatch handlers live in

    frob.app.ticket_runner._mutate (_brief) and _lifecycle (_work/_start), and

    AppConfig (src/frob/app/config.py) needs a ticket_cluster field to carry

    --cluster through the CLI. Narrowing/widening to the files this actually

    touches; original scope named stale/non-existent paths.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: 'Prior agent mapped the real surface for T-1243: frob.tickets._brief.compose_brief

    needs cluster-aware composition, frob.tickets._reporting.brief_ticket is the

    public entry point brief_ticket dispatches through, frob.tickets.__init__

    carries epic_rollup (descendant walk this ticket needs for dependency

    ordering), the CLI parsers for brief/start/work live in

    src/frob/_cli_parsers/_ticket/_query.py and _progress.py (not the

    _cli_parsers/_ticket.py monolith path named in the original scope, which was

    split by T-1270 before this ticket was filed), the dispatch handlers live in

    frob.app.ticket_runner._mutate (_brief) and _lifecycle (_work/_start), and

    AppConfig (src/frob/app/config.py) needs a ticket_cluster field to carry

    --cluster through the CLI. Narrowing/widening to the files this actually

    touches; original scope named stale/non-existent paths.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'Prior agent mapped the real surface for T-1243: frob.tickets._brief.compose_brief

    needs cluster-aware composition, frob.tickets._reporting.brief_ticket is the

    public entry point brief_ticket dispatches through, frob.tickets.__init__

    carries epic_rollup (descendant walk this ticket needs for dependency

    ordering), the CLI parsers for brief/start/work live in

    src/frob/_cli_parsers/_ticket/_query.py and _progress.py (not the

    _cli_parsers/_ticket.py monolith path named in the original scope, which was

    split by T-1270 before this ticket was filed), the dispatch handlers live in

    frob.app.ticket_runner._mutate (_brief) and _lifecycle (_work/_start), and

    AppConfig (src/frob/app/config.py) needs a ticket_cluster field to carry

    --cluster through the CLI. Narrowing/widening to the files this actually

    touches; original scope named stale/non-existent paths.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'Prior agent mapped the real surface for T-1243: frob.tickets._brief.compose_brief

    needs cluster-aware composition, frob.tickets._reporting.brief_ticket is the

    public entry point brief_ticket dispatches through, frob.tickets.__init__

    carries epic_rollup (descendant walk this ticket needs for dependency

    ordering), the CLI parsers for brief/start/work live in

    src/frob/_cli_parsers/_ticket/_query.py and _progress.py (not the

    _cli_parsers/_ticket.py monolith path named in the original scope, which was

    split by T-1270 before this ticket was filed), the dispatch handlers live in

    frob.app.ticket_runner._mutate (_brief) and _lifecycle (_work/_start), and

    AppConfig (src/frob/app/config.py) needs a ticket_cluster field to carry

    --cluster through the CLI. Narrowing/widening to the files this actually

    touches; original scope named stale/non-existent paths.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_query.py
  reason: 'Prior agent mapped the real surface for T-1243: frob.tickets._brief.compose_brief

    needs cluster-aware composition, frob.tickets._reporting.brief_ticket is the

    public entry point brief_ticket dispatches through, frob.tickets.__init__

    carries epic_rollup (descendant walk this ticket needs for dependency

    ordering), the CLI parsers for brief/start/work live in

    src/frob/_cli_parsers/_ticket/_query.py and _progress.py (not the

    _cli_parsers/_ticket.py monolith path named in the original scope, which was

    split by T-1270 before this ticket was filed), the dispatch handlers live in

    frob.app.ticket_runner._mutate (_brief) and _lifecycle (_work/_start), and

    AppConfig (src/frob/app/config.py) needs a ticket_cluster field to carry

    --cluster through the CLI. Narrowing/widening to the files this actually

    touches; original scope named stale/non-existent paths.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: 'Prior agent mapped the real surface for T-1243: frob.tickets._brief.compose_brief

    needs cluster-aware composition, frob.tickets._reporting.brief_ticket is the

    public entry point brief_ticket dispatches through, frob.tickets.__init__

    carries epic_rollup (descendant walk this ticket needs for dependency

    ordering), the CLI parsers for brief/start/work live in

    src/frob/_cli_parsers/_ticket/_query.py and _progress.py (not the

    _cli_parsers/_ticket.py monolith path named in the original scope, which was

    split by T-1270 before this ticket was filed), the dispatch handlers live in

    frob.app.ticket_runner._mutate (_brief) and _lifecycle (_work/_start), and

    AppConfig (src/frob/app/config.py) needs a ticket_cluster field to carry

    --cluster through the CLI. Narrowing/widening to the files this actually

    touches; original scope named stale/non-existent paths.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'Prior agent mapped the real surface for T-1243: frob.tickets._brief.compose_brief

    needs cluster-aware composition, frob.tickets._reporting.brief_ticket is the

    public entry point brief_ticket dispatches through, frob.tickets.__init__

    carries epic_rollup (descendant walk this ticket needs for dependency

    ordering), the CLI parsers for brief/start/work live in

    src/frob/_cli_parsers/_ticket/_query.py and _progress.py (not the

    _cli_parsers/_ticket.py monolith path named in the original scope, which was

    split by T-1270 before this ticket was filed), the dispatch handlers live in

    frob.app.ticket_runner._mutate (_brief) and _lifecycle (_work/_start), and

    AppConfig (src/frob/app/config.py) needs a ticket_cluster field to carry

    --cluster through the CLI. Narrowing/widening to the files this actually

    touches; original scope named stale/non-existent paths.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: 'Prior agent mapped the real surface for T-1243: frob.tickets._brief.compose_brief

    needs cluster-aware composition, frob.tickets._reporting.brief_ticket is the

    public entry point brief_ticket dispatches through, frob.tickets.__init__

    carries epic_rollup (descendant walk this ticket needs for dependency

    ordering), the CLI parsers for brief/start/work live in

    src/frob/_cli_parsers/_ticket/_query.py and _progress.py (not the

    _cli_parsers/_ticket.py monolith path named in the original scope, which was

    split by T-1270 before this ticket was filed), the dispatch handlers live in

    frob.app.ticket_runner._mutate (_brief) and _lifecycle (_work/_start), and

    AppConfig (src/frob/app/config.py) needs a ticket_cluster field to carry

    --cluster through the CLI. Narrowing/widening to the files this actually

    touches; original scope named stale/non-existent paths.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/config.py
  reason: 'Prior agent mapped the real surface for T-1243: frob.tickets._brief.compose_brief

    needs cluster-aware composition, frob.tickets._reporting.brief_ticket is the

    public entry point brief_ticket dispatches through, frob.tickets.__init__

    carries epic_rollup (descendant walk this ticket needs for dependency

    ordering), the CLI parsers for brief/start/work live in

    src/frob/_cli_parsers/_ticket/_query.py and _progress.py (not the

    _cli_parsers/_ticket.py monolith path named in the original scope, which was

    split by T-1270 before this ticket was filed), the dispatch handlers live in

    frob.app.ticket_runner._mutate (_brief) and _lifecycle (_work/_start), and

    AppConfig (src/frob/app/config.py) needs a ticket_cluster field to carry

    --cluster through the CLI. Narrowing/widening to the files this actually

    touches; original scope named stale/non-existent paths.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_tickets_brief.py
  reason: 'Prior agent mapped the real surface for T-1243: frob.tickets._brief.compose_brief

    needs cluster-aware composition, frob.tickets._reporting.brief_ticket is the

    public entry point brief_ticket dispatches through, frob.tickets.__init__

    carries epic_rollup (descendant walk this ticket needs for dependency

    ordering), the CLI parsers for brief/start/work live in

    src/frob/_cli_parsers/_ticket/_query.py and _progress.py (not the

    _cli_parsers/_ticket.py monolith path named in the original scope, which was

    split by T-1270 before this ticket was filed), the dispatch handlers live in

    frob.app.ticket_runner._mutate (_brief) and _lifecycle (_work/_start), and

    AppConfig (src/frob/app/config.py) needs a ticket_cluster field to carry

    --cluster through the CLI. Narrowing/widening to the files this actually

    touches; original scope named stale/non-existent paths.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'Adding --cluster to AppConfig requires wiring it through

    src/frob/app/_config_external.py''s _STRING_FIELDS tuple (WIRE001: a CLI

    dest that AppConfig.from_external silently drops otherwise) and through

    design/frob.strata''s tickets_ledger/testsuite interface declarations

    (SELFAUDIT001: new public symbols must be declared, not just exported).

    Both are mechanical consequences of the T-1243 cluster feature, not new

    scope creep.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: design/frob.strata
  reason: 'Adding --cluster to AppConfig requires wiring it through

    src/frob/app/_config_external.py''s _STRING_FIELDS tuple (WIRE001: a CLI

    dest that AppConfig.from_external silently drops otherwise) and through

    design/frob.strata''s tickets_ledger/testsuite interface declarations

    (SELFAUDIT001: new public symbols must be declared, not just exported).

    Both are mechanical consequences of the T-1243 cluster feature, not new

    scope creep.

    '
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_tickets_brief.py::TestClusterBrief::test_composes_one_briefing_for_the_whole_cluster
- tests/test_tickets_brief.py::TestClusterDescendants::test_dependency_order_respects_intra_cluster_blocked_by
- tests/test_tickets_lease.py::TestWorkCluster::test_leases_every_dispatchable_member_into_one_worktree
- tests/test_tickets_lease.py::TestClusterScopeConflict::test_refuses_when_union_scope_collides_with_a_foreign_lease
designated_repro_test: null
acceptance:
- text: 'GIVEN frob ticket brief --cluster <epic-or-story-id> THEN one briefing is
    emitted covering every doable descendant in dependency order: shared playbook
    rules once, per-ticket body+acceptance+scope, the union scope lease, and the expected
    land cadence (one land per ticket, not one mega-land)'
  evidence:
  - tests/test_tickets_brief.py::TestClusterBrief::test_composes_one_briefing_for_the_whole_cluster
  - tests/test_tickets_brief.py::TestClusterDescendants::test_dependency_order_respects_intra_cluster_blocked_by
- text: GIVEN frob ticket work --cluster <id> THEN one worktree is created/reused
    with natives built once and every ticket in the cluster leased to it, so an agent
    pays worktree warmup, playbook read, and natives build exactly once per cluster
    instead of once per ticket
  evidence:
  - tests/test_tickets_lease.py::TestWorkCluster::test_leases_every_dispatchable_member_into_one_worktree
- text: GIVEN two clusters with overlapping union scopes THEN the second lease attempt
    fails loud naming the conflict, preserving the disjoint-scope dispatch guarantee
  evidence:
  - tests/test_tickets_lease.py::TestClusterScopeConflict::test_refuses_when_union_scope_collides_with_a_foreign_lease
threat: null
component: null
---
User directive 2026-07-29: agents should receive a series of related tickets in one mission to avoid cold-start cost (worktree creation, playbook read, natives build, graph warm) being paid per ticket. The tier system (epic/story/ticket) and parent edges already express the grouping; frob ticket brief (T-0568) and frob ticket work already exist per-ticket. This adds the cluster form: dependency-ordered doable descendants of an epic/story as one mission with a union scope lease. Serial-cluster dispatch is already the coordinator practice (drive memory); this makes it a first-class frob verb instead of hand-assembled prompts.