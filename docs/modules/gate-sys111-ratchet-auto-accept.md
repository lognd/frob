# SYS111 ratchet ceiling: branch-own via addition auto-accept (T-4633)

Standalone page -- `docs/modules/gates.md` was leased by T-4111 for this
ticket's entire duration (the same lease-conflict shape T-4605's own body
already tracks for T-4114/T-4115/T-4221/T-3962/T-3961). Once
`docs/modules/gates.md` is free: fold this section into it next to the
existing SYS111 discussion (the `fix_sys111_capability_ratchet_sync`
T-2001 paragraphs, "Rule catalog" table row) and delete this file; a
fold-in item has been appended to T-4605's body so the fold happens the
same way every other lease-blocked SYS111/gates.md doc addition has.

## Problem (measured three times: T-4508 x2, T-4111)

A ticket declares a new `via` site for a node/atom in `design/frob.strata`
and bumps the matching `accepted_count` in
`docs/design/registry/capability-via-ratchet.lock.json` to the count it
observes on its own branch. By the time the serial land for that ticket
actually runs, `dev` has moved -- some other, unrelated ticket already
landed and (legitimately) grew the SAME node/atom's via-list further. The
land's own composed-tree SYS111 check (`frob.strata._effects.
capability_ratchet_violations`, wired via `frob.gates._sys.
sys111_findings_touching` into `frob.tickets._land_squash.
_refuse_if_selfaudit_findings_in_touched_files`, T-3324/T-4596) then
observes a count higher than what THIS branch's own `accepted_count` bump
anticipated, and refuses with "grew above the committed ceiling" -- even
though every bit of the growth this branch is responsible for is exactly
the site it itself declared.

This is a DIFFERENT failure mode than the one `fix_sys111_capability_
ratchet_sync` (T-2001, `--fix` Tier-A handler) already closes: that
handler re-baselines the ceiling for a human-authored widening BEFORE a
commit lands, as a `frob check --fix` convenience on the author's own worktree. It
does nothing for the race described here, which happens AFTER the ticket's
own commit is already final and squashed, at land time, against a `dev`
that has since moved out from under it.

## Fix: branch-own via-growth auto-accept at land composed-tree check time

Same posture as the existing T-4495/T-4563/T-4596 testsuite-glob
auto-accept in `frob.strata._effects.capability_ratchet_violations`
(module docstring's T-4495 section) -- generalized from "any `testsuite`
node glob-form via" to "any node/atom pair whose ceiling breach is fully
accounted for by THIS branch's own via additions", and gated the same
way: writes the committed lock file ONLY while `_land_commit_in_progress`
reads `True` (a land's own pre-commit composed-tree check, whose write
lands inside that same not-yet-committed changeset); any other caller
(interactive `frob check`, the detached post-land sweep) observes the
growth without writing anything and reports it as an ordinary
`CapabilityRatchetViolation`.

- `frob.strata._effects._branch_own_via_growth(root)`: `{"<node>::<atom>":
  N}` for every via-list growth `design/frob.strata` itself shows between
  its committed `HEAD` blob (`git show HEAD:design/frob.strata`) and the
  CURRENT working-tree content under `root`. A land's composed-tree check
  runs with `root`'s git `HEAD` still at the pre-squash tip and the
  staged, not-yet-committed squash content already written into the
  working tree -- so this diff is EXACTLY the branch's own addition, with
  no base-ref parameter needing to thread through `frob.gates._sys.
  sys111_findings_touching`'s fixed `(root, files)` signature (that
  module was leased by another in-progress ticket, T-4212, for this
  ticket's whole duration, so its signature could not grow one here).
- `frob.strata._effects._capability_ratchet_growth_finding` now also
  auto-accepts (in addition to the existing testsuite-glob branch) when
  `count - accepted <= branch_growth.get(key, 0)` and a land holds the
  write -- i.e. the ceiling breach is no larger than what this branch's
  own diff added. Growth beyond that (an undeclared site, or growth some
  OTHER ticket already landed) is NOT covered and still refuses exactly as
  before -- this auto-accept only ever narrows the gap a stale ceiling
  bump left, never widens what counts as legitimate growth.
- The written lock entry's `reason` names the landing ticket when known:
  `frob.tickets._land_squash._refuse_if_selfaudit_findings_in_touched_
  files` sets `FROB_LAND_TICKET_ID` (env var, same thread-through shape as
  `FROB_LAND_LOCK_ROOT_ENV`/T-4596) for the duration of its in-process
  SYS111 gate call via `frob.strata._effects._land_ticket_id_env`, and
  `_branch_own_via_growth_reason` reads it back (falls back to a generic
  reason when unset, e.g. an interactive-check codepath that never sets
  it).

## Positive controls

- A branch whose growth is entirely its own via additions lands: SYS111
  observes the ceiling breach exactly matches `_branch_own_via_growth`'s
  count for that key, auto-accepts, and the lock file is rewritten with a
  reason naming the ticket (`tests/unit/strata/test_selfconform.py::
  TestBranchOwnViaGrowth.test_branch_own_growth_auto_accepts`).
- A branch whose growth includes an undeclared site (or growth another
  already-landed ticket is responsible for) still refuses: the needed
  growth exceeds what the branch's own diff shows, so no auto-accept
  fires and the lock is left untouched (`tests/unit/strata/
  test_selfconform.py::TestBranchOwnViaGrowth.
  test_growth_beyond_branch_own_addition_still_refuses`).

A bare `frob check` (outside a land, `_land_commit_in_progress` reading
`False`) keeps refusing unconditionally, same as the pre-existing
testsuite-glob carve-out.
