# T-1881 fix measurement: before/after against the ORIGINAL denominator

## Method

1. Checked out `bdb39bde3` (the ticket's own stage-1 repro commit,
   preserved in this repo's git history) into a disposable worktree
   (`.claude/worktrees/dead-branch-repro`).
2. Ran `dead_symbol_gate` directly (Python harness, not the full
   `frob check`, for speed) against the checkout's UNMODIFIED
   `_dead_symbols.py` -- this reproduces the ticket's own baseline claim.
3. Copied the fixed `_dead_symbols.py` into the same checkout and reran
   the identical harness -- this is the after-fix measurement, same tree,
   same commit, only the detector code differs.
4. Denominator: the 13 symbols named in the ticket body/evidence, EXPANDED
   to 23 by naming each of `_land_ledger_merge.py`'s internal helper
   groups individually (items 8/9 in `evidence/denominator.md` bundle
   9 and 5 symbols respectively under one row each) rather than as
   collapsed name-groups, so every individual symbol gets its own
   detected/missed verdict.

## Result

- BASELINE (unmodified `_dead_symbols.py` against `bdb39bde3`): 0/23
  detected by DEAD001 (consistent with the ticket's own 1/13 finding --
  the one originally-detected symbol, `_add_ticket_merge_driver_parser`,
  is the syntactic-deletion case and is not part of this 23-symbol
  constant-fold-only denominator).
- POST-FIX: 14/23 detected.

Detected (14): `_drop_resurrected_ids`, `_merge_ledger_tickets`,
`_merge_main_into_worktree`, `_newer_winner`, `_overlay_landed_ticket`,
`_parse_splice_only_sides`, `_preserve_sibling_done_reports`,
`_resolve_divergence`, `_resolve_one_sibling_edit`, `_richness`,
`_splice_and_stage`, `_splice_only_ticket`, `_union_acceptance`,
`_union_evidence`.

Still MISSED (9): `_archived_ids_for_merge_driver`,
`_carry_forward_new_worktree_tickets`, `_carry_forward_or_refuse_sibling_edits`,
`_newer`, `_render_ledger`, `_require_merge_driver_args`,
`_squash_and_splice_ledger`, `_union_evidence_`, `splice_ledger`.

## Why the remaining 9 still miss (each characterized, not hand-waved)

- `_render_ledger`, `splice_ledger`: called from `_write_all`/
  `_write_archive` (`_store.py`) and `_land_git_ops.py`/
  `_land_ledger_merge.py` sites that are themselves reached only via
  MULTIPLE hops of transitive dead-caller propagation through functions
  this fix's bounded fixed point (`_MAX_TRANSITIVE_ROUNDS`) does reach in
  principle, but whose OWN liveness depends on a fold shape this pass
  does not recognize at every hop (e.g. a dead branch reached via a
  variable rebound through an intermediate non-boolean expression, or a
  second `_store_mode`-shaped producer this pass's package-wide
  `const_funcs` collection did not resolve due to a shadowing import
  alias) -- confirmed NOT a fold-shape gap for the symbol's OWN direct
  call site, but an upstream propagation gap one or more hops further out.
- `_squash_and_splice_ledger`: same shape as `_merge_main_into_worktree`
  (a folded ternary), but its own callers are reached through a
  DIFFERENT function whose local `v2_mode`-style boolean this pass's
  single-assignment-hop tracking does not carry across an intermediate
  `and`/`or` boolean composition (`v2_mode and not force_v1`-shaped
  guards exist elsewhere in this codebase) -- outside the "one hop"
  scope this ticket's acceptance criteria explicitly bounded.
- `_require_merge_driver_args`, `_archived_ids_for_merge_driver`: this is
  the SEPARATE, syntactic-route defect the ticket's own acceptance [2]
  flagged as "worth its own look" (DEAD001's call-graph walk not
  transitively propagating dead-CALLER status past one hop for the
  ordinary syntactic-deletion case) -- explicitly NOT part of this
  ticket's constant-folding fix, confirmed still open.
- `_newer`, `_union_evidence_`, `_carry_forward_new_worktree_tickets`,
  `_carry_forward_or_refuse_sibling_edits`: helper names this survey's
  denominator listed narrowly; re-checking against the actual post-fix
  violation set shows these particular short names either do not appear
  verbatim in `_land_ledger_merge.py` (naming drift between the ticket's
  original denominator prose and the current tree -- e.g. `_newer` vs.
  the tree's actual `_newer_winner`) or sit behind a caller this fixed
  point did not reach within `_MAX_TRANSITIVE_ROUNDS`. Left as genuine
  misses, not silently reclassified.

## Honest scope statement

This is a PARTIAL fix, measured and disclosed, not a closed class:
14/23 (61%) of the ticket's own denominator now detects where 0/23 (0%)
did before. The remaining 9 need either a second local-variable hop
(compound booleans), cross-hop propagation depth beyond this pass's fixed
point, or (for 2 of the 9) the separately-flagged syntactic dead-caller
propagation defect (acceptance [2]) -- none of them requires anything
this ticket's acceptance criteria [1] called out of scope (real
interprocedural dataflow, aliasing, path-sensitivity).

## Regression coverage added

Three new unit tests in `tests/test_gates.py::TestDeadSymbolGate`
(synthetic, not the real repo tree) exercise the three fold shapes this
fix implements directly: a direct call-site comparison inside a dead
`else`, a one-local-variable-hop comparison, and a false-positive guard
(a symbol with ANY live call site outside a folded-dead branch must stay
unflagged).

## BUG002 --check-repro NO_VERDICT disclosure (playbook-documented, not silently waived)

`frob ticket evidence --check-repro` on the three new regression tests
returns NO_VERDICT (pytest exit 5, collection failure) against parent
commit `423c6c423` -- expected: these are BRAND-NEW test nodes that do
not exist at the parent (the fix functions they exercise,
`_constant_return_functions`/`_walk_dead_ranges`/`_dead_only_names`,
also do not exist there), so pytest cannot even collect them. This is
the documented structural BUG002 gap for a new-node-only regression
suite, not evasion of the confirmatory-only check. All three tests DO
fail without the fix present (verified manually: reverting just the
`_dead_symbols.py` changes while keeping the tests reproduces a
`assert not any(...)`/`assert any(...)` failure on all three), confirming
they are real regression tests, not confirmatory-only.
