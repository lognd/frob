---
id: T-1269
title: 'ticket land --plan: atomic design-phase land with automatic draft finalization'
state: done
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_draft_finalize.py
- docs/modules/tickets.md
- tests/test_ticket_land.py
- src/frob/tickets/_models.py
- src/frob/tickets/_land_git_ops.py
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/tickets/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/_ticket.py
  reason: 'src/frob/_cli_parsers/_ticket.py and src/frob/app/ticket_runner.py both
    became packages (directories) after this ticket was filed; DOC006 flagged the
    stale single-file globs as untracked paths (T-draft-48cb3b39 NEGEXIST/DOC/WAIVE/COV
    burn-down).

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/_ticket/**
  reason: 'src/frob/_cli_parsers/_ticket.py and src/frob/app/ticket_runner.py both
    became packages (directories) after this ticket was filed; DOC006 flagged the
    stale single-file globs as untracked paths (T-draft-48cb3b39 NEGEXIST/DOC/WAIVE/COV
    burn-down).

    '
  actor: logan
  at: '2026-08-03'
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
- op: remove
  glob: src/frob/_cli_parsers/_ticket/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_draft_finalize.py
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
  glob: tests/test_ticket_land.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'Prior agent mapped the real surface for T-1269: the new land_plan entry

    point belongs in src/frob/tickets/_land.py (already declared scope)

    reusing existing safe primitives from _land_git_ops.py (_porcelain_dirty,

    _rev_parse), _draft_finalize.py (finalize_draft, already declared scope),

    and _models.py (a new LandError variant for the TICK-gate-dirty outcome).

    The CLI wiring for --plan lives in _cli_parsers/_ticket/_progress.py

    (land parser) and the dispatch handler in app/ticket_runner/_land_cmd.py,

    plus AppConfig.ticket_land_plan. Widening to the files this actually

    touches; the id-allocator language in the original ticket refers to

    _draft_finalize.py''s existing finalize_draft/_next_ticket_id, already in

    scope.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'Prior agent mapped the real surface for T-1269: the new land_plan entry

    point belongs in src/frob/tickets/_land.py (already declared scope)

    reusing existing safe primitives from _land_git_ops.py (_porcelain_dirty,

    _rev_parse), _draft_finalize.py (finalize_draft, already declared scope),

    and _models.py (a new LandError variant for the TICK-gate-dirty outcome).

    The CLI wiring for --plan lives in _cli_parsers/_ticket/_progress.py

    (land parser) and the dispatch handler in app/ticket_runner/_land_cmd.py,

    plus AppConfig.ticket_land_plan. Widening to the files this actually

    touches; the id-allocator language in the original ticket refers to

    _draft_finalize.py''s existing finalize_draft/_next_ticket_id, already in

    scope.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: 'Prior agent mapped the real surface for T-1269: the new land_plan entry

    point belongs in src/frob/tickets/_land.py (already declared scope)

    reusing existing safe primitives from _land_git_ops.py (_porcelain_dirty,

    _rev_parse), _draft_finalize.py (finalize_draft, already declared scope),

    and _models.py (a new LandError variant for the TICK-gate-dirty outcome).

    The CLI wiring for --plan lives in _cli_parsers/_ticket/_progress.py

    (land parser) and the dispatch handler in app/ticket_runner/_land_cmd.py,

    plus AppConfig.ticket_land_plan. Widening to the files this actually

    touches; the id-allocator language in the original ticket refers to

    _draft_finalize.py''s existing finalize_draft/_next_ticket_id, already in

    scope.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'Prior agent mapped the real surface for T-1269: the new land_plan entry

    point belongs in src/frob/tickets/_land.py (already declared scope)

    reusing existing safe primitives from _land_git_ops.py (_porcelain_dirty,

    _rev_parse), _draft_finalize.py (finalize_draft, already declared scope),

    and _models.py (a new LandError variant for the TICK-gate-dirty outcome).

    The CLI wiring for --plan lives in _cli_parsers/_ticket/_progress.py

    (land parser) and the dispatch handler in app/ticket_runner/_land_cmd.py,

    plus AppConfig.ticket_land_plan. Widening to the files this actually

    touches; the id-allocator language in the original ticket refers to

    _draft_finalize.py''s existing finalize_draft/_next_ticket_id, already in

    scope.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/config.py
  reason: 'Prior agent mapped the real surface for T-1269: the new land_plan entry

    point belongs in src/frob/tickets/_land.py (already declared scope)

    reusing existing safe primitives from _land_git_ops.py (_porcelain_dirty,

    _rev_parse), _draft_finalize.py (finalize_draft, already declared scope),

    and _models.py (a new LandError variant for the TICK-gate-dirty outcome).

    The CLI wiring for --plan lives in _cli_parsers/_ticket/_progress.py

    (land parser) and the dispatch handler in app/ticket_runner/_land_cmd.py,

    plus AppConfig.ticket_land_plan. Widening to the files this actually

    touches; the id-allocator language in the original ticket refers to

    _draft_finalize.py''s existing finalize_draft/_next_ticket_id, already in

    scope.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'Prior agent mapped the real surface for T-1269: the new land_plan entry

    point belongs in src/frob/tickets/_land.py (already declared scope)

    reusing existing safe primitives from _land_git_ops.py (_porcelain_dirty,

    _rev_parse), _draft_finalize.py (finalize_draft, already declared scope),

    and _models.py (a new LandError variant for the TICK-gate-dirty outcome).

    The CLI wiring for --plan lives in _cli_parsers/_ticket/_progress.py

    (land parser) and the dispatch handler in app/ticket_runner/_land_cmd.py,

    plus AppConfig.ticket_land_plan. Widening to the files this actually

    touches; the id-allocator language in the original ticket refers to

    _draft_finalize.py''s existing finalize_draft/_next_ticket_id, already in

    scope.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'Prior agent mapped the real surface for T-1269: the new land_plan entry

    point belongs in src/frob/tickets/_land.py (already declared scope)

    reusing existing safe primitives from _land_git_ops.py (_porcelain_dirty,

    _rev_parse), _draft_finalize.py (finalize_draft, already declared scope),

    and _models.py (a new LandError variant for the TICK-gate-dirty outcome).

    The CLI wiring for --plan lives in _cli_parsers/_ticket/_progress.py

    (land parser) and the dispatch handler in app/ticket_runner/_land_cmd.py,

    plus AppConfig.ticket_land_plan. Widening to the files this actually

    touches; the id-allocator language in the original ticket refers to

    _draft_finalize.py''s existing finalize_draft/_next_ticket_id, already in

    scope.

    '
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_ticket_land.py::TestLandPlan::test_merges_and_finalizes_every_draft_atomically
- tests/test_ticket_land.py::TestLandPlan::test_merge_conflict_aborts_and_refuses
- tests/test_ticket_land.py::TestLandPlan::test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge
- tests/test_ticket_land.py::TestLandPlan::test_dry_run_unwinds_the_merge
- tests/test_ticket_land.py::TestLandPlan::test_cli_dispatches_to_land_plan_and_reports
designated_repro_test: null
acceptance:
- text: 'GIVEN a planner worktree containing only docs plus ledger changes (no closeable
    worked ticket) WHEN frob ticket land --plan --worktree PATH runs THEN it performs
    the whole chain atomically: merge via the ledger driver, finalize EVERY incoming
    draft id to the next free real ids in one allocator-locked ledger write (cross-references
    rewritten), verify TICK gate clean, and commit -- one command, one commit for
    the finalization, no hand-assigned ids'
  evidence:
  - tests/test_ticket_land.py::TestLandPlan::test_merges_and_finalizes_every_draft_atomically
  - tests/test_ticket_land.py::TestLandPlan::test_dry_run_unwinds_the_merge
  - tests/test_ticket_land.py::TestLandPlan::test_cli_dispatches_to_land_plan_and_reports
- text: GIVEN any failure mid-chain THEN the operation unwinds completely (no half-merged
    ledger, no partially-renumbered drafts) and names the manual remedy
  evidence:
  - tests/test_ticket_land.py::TestLandPlan::test_merge_conflict_aborts_and_refuses
  - tests/test_ticket_land.py::TestLandPlan::test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge
threat: null
component: null
---
User directive 2026-07-29: renumbering must be atomic and automatic. Evidence from this drive: landing four design-phase planner worktrees required a guarded plain git merge (FROB_LAND_INTERNAL=1) plus 15 hand-assigned frob ticket renumber calls across 4 batches, because frob ticket land (T-0176) requires a closeable ticket and its draft-finalization path only runs for worked-ticket lands. Also fix the stale TICK002 remedy text that still says 'once T-0176 lands' (it landed). Builds on the existing finalize_draft_for_land machinery (_draft_finalize.py) and the T-0162 id allocator; ledger-v2 (T-1255 renumber child) later absorbs the same behavior for the file-per-ticket store.