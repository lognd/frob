---
id: T-2587
title: Wire frob ticket promote into the T-2563 ledger mirror so a promoted id is
  visible on main immediately, not only after land
state: in-progress
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/app/ticket_runner/_ledger_mirror.py
- src/frob/app/ticket_runner/__init__.py
- docs/modules/tickets-lifecycle.md
- tests/unit/test_ticket_runner_ledger_mirror.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: T-2587's new mirror_promote_to_primary/doc anchor and its dedicated unit
    tests need these two paths writable/in-scope
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/unit/test_ticket_runner_ledger_mirror.py
  reason: T-2587's new mirror_promote_to_primary/doc anchor and its dedicated unit
    tests need these two paths writable/in-scope
  actor: logan
  at: '2026-08-19'
- op: add
  glob: design/frob.strata
  reason: mirror_promote_to_primary's shutil.rmtree call is a new fs.write capability
    site needing declaration on the cli node
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

T-2197 fixed two real gaps in `frob ticket promote` run from a worktree:
`finalize_draft` (src/frob/tickets/_draft_finalize.py) now COMMITS its own
full rename (ledger + every code reference) atomically, where before it
left everything uncommitted for a caller that never existed (worse than
T-2197's original description -- not merely worktree-branch-only, but
never durably written at all), and it now logs a loud ERROR naming the
worktree-only visibility gap when `root` is not the resolved primary
checkout.

What T-2197 did NOT do, because the only file that could do it
(`src/frob/app/ticket_runner/_ledger_mirror.py`, T-2563's shared
worktree-to-primary ledger mirror) was under another agent's live lease
for the whole of T-2197's work: wire `promote` into
`mirror_ledger_change_to_primary` so a promoted id is actually VISIBLE on
main immediately, the same way `scope`/`block`/`attach`/`tier`/... already
are, instead of only a warning that says so.

This needs real design, not a copy-paste of the existing mirror: `promote`
mirrors a git RENAME across potentially many `frob:ticket`/`frob:tests`/
... directive lines throughout the tracked tree (via `renumber_one`), not
just the ticket's own ledger pathspec the existing mirror is scoped to
(`_ledger_pathspecs`) -- mirroring the FULL rename the same
pathspec-limited way risks carrying a dirty worktree's unrelated
uncommitted SOURCE edits onto main, the exact hazard
`mirror_ledger_change_to_primary`'s own docstring already documents as
why it stays ledger-only. A safe design likely mirrors ONLY the ticket's
own ledger pathspec (old_id gone, new_id present) and leaves the
cross-file directive-reference rewrite worktree-local until the ticket's
own work lands (matching how renumber's code-reference rewrites already
ride along with a land today) -- but that tradeoff needs to be made
explicitly, with a test, not assumed.

## Plan

1. Read `mirror_ledger_change_to_primary`/`_mirror_target`/`_ledger_
   pathspecs` (T-2563) and `finalize_draft`/`_commit_and_warn_promote`
   (T-2197) together.
2. Decide and document the mirrored surface for `promote` (ledger-only,
   per the reasoning above, unless investigation finds a safer way to
   mirror the code-reference rewrites too).
3. Add `"promote"` handling -- likely NOT a bare addition to `MIRRORED_
   LEDGER_VERBS` (that set assumes a single-file-ish pathspec set already
   committed by the generic auto-commit sweep `promote` is excluded from
   for its own reasons) -- probably a dedicated call from `_promote`'s
   CLI handler after `_commit_and_warn_promote` succeeds.
4. Replace T-2197's warning-only fallback with "mirrored, now visible on
   main" when it succeeds, keeping the warning as the fallback for when
   mirroring is skipped (a land in progress, same as the existing
   mirror's own fallback).
5. Tests: a worktree promote becomes visible on the primary checkout's
   own ledger without requiring a land, mirroring T-2563's own test
   shape (tests/unit/test_ticket_runner_ledger_mirror.py).
