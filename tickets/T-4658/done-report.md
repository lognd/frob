## Done report

T-4658 -- Ids are assigned once at new: renumbering inside a worktree is
refused

## Changed

- src/frob/tickets/_new_renumber.py:
    New private helper `_refuse_renumber_inside_worktree(root)`: resolves
    `root`, checks it against `.claude/worktrees/` (via the existing
    `_is_agent_worktree_path` from `_worktree_sweep.py`, imported rather
    than duplicated), and if it matches, logs a WARNING naming the
    detected worktree path and returns
    `Err(TicketError.WorktreeLeaseViolation)` -- reusing the existing
    enum member rather than adding a new one, since the ticket's scope
    (this file, _renumber_v2.py, and the test file only) does not include
    _models.py.
    Wired into `renumber()` (bulk renumber) and `renumber_one()`
    (single-id rename, before its v1/v2 dispatch, so both backends are
    covered from one call site) as the FIRST check, before
    `enforce_worktree_lease` -- this is a stricter, unconditional
    refusal: a worktree correctly leased to itself passes
    `enforce_worktree_lease` fine today and could still renumber, which
    is exactly the measured bug.
    `new_ticket()`: added an INFO log line after successful allocation,
    `"tickets: allocated %s (cwd=%s, root=%s)"`, per the ticket's logging
    requirement.

- src/frob/tickets/_renumber_v2.py:
    `renumber_one_v2()` also calls `_refuse_renumber_inside_worktree`
    defensively (it is itself a public v2-mode entry point some caller
    could reach directly, not only via `renumber_one`'s dispatch).

- tests/unit/test_ids_assigned_once.py (NEW): 5 tests.
    test_renumber_refused_inside_worktree -- POSITIVE CONTROL. Builds a
      tmp_path shaped like `<tmp>/.claude/worktrees/t-9999/`, calls
      `renumber()` on it, asserts Err(WorktreeLeaseViolation) and that
      nothing under `tickets/` was written. Fails on dev today (renumber
      succeeds); passes after this leaf.
    test_renumber_one_refused_inside_worktree -- same refusal for the
      single-id rename entry point.
    test_renumber_one_v2_refused_inside_worktree -- same refusal for the
      v2-mode backend directly.
    test_refusal_helper_allows_a_non_worktree_root -- companion control:
      the helper does not simply always refuse; a non-worktree-shaped
      root is allowed through.
    test_concurrent_new_allocates_distinct_ids -- two `new_ticket` calls
      from two threads against the same (non-worktree) root receive
      distinct ids; proves the allocator_lock property end to end rather
      than trusting the lock exists.

## WHY

Kernel decoupling (T-4651/T-4652): ids must be allocated exactly once, at
`frob ticket new` in the root checkout; renumbering and draft promotion
are root/ledger-only operations performed by `frob ticket land`, never
inside a dispatched worktree. Measured this week: draft ids renumbered
INSIDE worktrees and concurrent agents racing each other's renumbers
(T-4590/T-4596, T-4633, T-4636/T-4642), and duplicate promotions
(T-4597/T-4602 vs T-4605) from the same root cause -- no structural
seam preventing a worktree from renumbering at all. `enforce_worktree_
lease` alone does not catch this because it only refuses a MISMATCHED
lease; a worktree correctly leased to itself sails through.

## Acceptance criteria -> evidence

[1] Given a checkout under .claude/worktrees/, renumber is refused with a
    named, logged error, ledger unchanged
    -> tests/unit/test_ids_assigned_once.py::test_renumber_refused_inside_worktree
[2] POSITIVE CONTROL, fails on dev today, passes after this leaf
    -> tests/unit/test_ids_assigned_once.py::test_renumber_refused_inside_worktree
[3] Two concurrent `frob ticket new` calls in the root get distinct ids
    -> tests/unit/test_ids_assigned_once.py::test_concurrent_new_allocates_distinct_ids

All three bound via `frob ticket evidence T-4658 <node> --accepts <n>
--base-ref dev`, rebound after the LAST commit (fe0aad1de, shared with
T-4657 in this same worktree/series) per the pre-READY checklist's item 8.

## Named error reused (not new)

`TicketError.WorktreeLeaseViolation` is reused rather than adding a new
enum variant -- the ticket's own scope excludes `_models.py`, and the
log message (not the enum tag) carries the specific "renumber refused,
this is a .claude/worktrees/ agent checkout, ids are assigned once at
`frob ticket new`" diagnosis. Documented in the helper's own docstring.

## Regression check (existing renumber/lease test suites, unaffected)

Ran (not just collected) after the change, all pass:
  tests/test_tickets.py, tests/test_tickets_collision.py,
  tests/test_tickets_ledger_concurrency.py,
  tests/test_ticket_store_stale_snapshot.py: 271 passed
  tests/test_ticket_leases.py, tests/test_ticket_leases_cross_worktree.py,
  tests/unit/test_draft_finalize_attachments.py,
  tests/ticket_land_suite/test_draft.py: 222 passed
This is a NEW, additive refusal that only fires for a root path shaped
like `.claude/worktrees/**` -- every existing test's tmp_path root is
outside that shape, so none needed updating.

## Filed
none -- no out-of-scope work discovered.

## Pre-READY checks

`frob check --only arch --files src/frob/tickets/_new_renumber.py --files
src/frob/tickets/_renumber_v2.py --files tests/unit/test_ids_assigned_once.py
--base dev`:
  pass gate:frob-arch (20 warnings, 36 waived, 549 pattern-recommendation
    suggestions, all pre-existing repo-wide, none new to this ticket's
    files)
  -> clean, no ARCH001/LARGE001 on this ticket's files.

`frob check --only coverage --files <same three, plus T-4657's files, run
jointly>`:
  Only pre-existing COV007 (waived) hits on `_new_renumber.py`'s existing
  private symbols (`_allocate_ticket_id`, `_warn_empty_scope_on_new`,
  `_warn_over_broad_scope_on_new`) -- none of them the new
  `_refuse_renumber_inside_worktree` helper, which is private (leading
  underscore) and correctly carries no frob:doc/frob:tests directive,
  matching this module's existing convention for private helpers (e.g.
  `_refuse_if_other_worktree_holds_live_lease` has none either). Zero
  COV001/COV002 attributable to `_new_renumber.py`/`_renumber_v2.py`/
  `test_ids_assigned_once.py`.
  -> clean for this ticket's files.

`ruff check src/frob/tickets/_new_renumber.py
  src/frob/tickets/_renumber_v2.py tests/unit/test_ids_assigned_once.py`:
  All checks passed! (one fix: dropped an unused `pytest` import from the
  test file.)
`ruff format --check` (all three): unchanged.
`ty check` (all three): All checks passed! (one fix: typed the
  `results` list as `list[Result[Ticket, TicketError] | None]` instead of
  `list[object]`, replacing two `# type: ignore` comments with real
  narrowing via `first`/`second` locals.)

Cross-ticket lease scan: `git diff --name-only dev...HEAD` for this
worktree contains only files declared in T-4657's or T-4658's own scope
(plus their own tickets/<id>/ticket.md); `grep -l "<path>"
.git/frob-leases/*.json` for every touched path returns only T-4657.json/
T-4658.json -- no cross-ticket lease conflicts.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_ids_assigned_once.py::test_renumber_refused_inside_worktree` (pytest node id, verified passing when recorded)
- `tests/unit/test_ids_assigned_once.py::test_concurrent_new_allocates_distinct_ids` (pytest node id, verified passing when recorded)
