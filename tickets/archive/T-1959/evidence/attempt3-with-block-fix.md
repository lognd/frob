# T-1959 attempt 3: with/async-with recursion, plus a decisive re-characterization of the denominator

## Method

Same harness and denominator as T-1881/attempt 1/attempt 2 (23 symbols
at `bdb39bde3`, `tickets/T-1881/evidence/denominator.md`). Cut a
disposable detached-HEAD checkout of `bdb39bde3` (`/tmp/dead-repro`,
outside this worktree and outside the repo's own `.claude/worktrees/`
tree so it carries no ticket lease), copied the candidate detector in,
and ran `dead_symbol_gate` directly against the real `frob.graph.
build_graph` snapshot (not the full `frob check` pipeline, for speed --
matches T-1881's own method).

## The decisive finding: 6 of the 9 "misses" are not detection gaps at all

Before writing any code, each of the 9 named misses was checked against
`_declared_referenced_symrefs` (DEAD001's own DECLARED-reference
exemption: a symbol carrying its own `frob:tests`/`frob:invariant`
directive is wired by definition, regardless of any call-graph or
constant-fold analysis). Six of the nine carry this directive directly
above their own `def`:

- `_carry_forward_new_worktree_tickets` -- `frob:tests` (T-0637)
- `_carry_forward_or_refuse_sibling_edits` -- five `frob:tests` (T-1721)
- `_newer` -- `frob:invariant INV-043` plus eight `frob:tests`
- `splice_ledger` -- confirmed via `_declared_referenced_symrefs` output
  directly (`frob:tests` elsewhere in its own directive block)
- `_archived_ids_for_merge_driver` -- two `frob:tests` (T-1437), already
  flagged as this exact shape by attempt 1's own evidence
- `_squash_and_splice_ledger` -- `frob:tests` (T-0907/T-1036)

**These six can never be flagged by any correct DEAD001 change without
weakening or removing the DECLARED-reference exemption itself** -- that
exemption is not incidental, it is the gate's own mechanism for a symbol
reached only dynamically (the exact rescue this module's docstring
documents for `getattr`-string dispatch and pydantic validators). The
ticket's own instruction is explicit: "do not chase the ratio by
loosening detection." Weakening the exemption to catch these six would
reintroduce the false-positive class DEAD001 was built to avoid. This is
a structural, provable, permanent ceiling on the denominator, not a
remaining implementation gap -- characterized here because neither
T-1881 nor attempt 1/2's evidence identified it; both treated all 9 as
open detection gaps.

Verified via direct harness call (`_declared_referenced_symrefs(snap)`
against the real `bdb39bde3` `GraphSnapshot`) -- all six symrefs are
present in the returned set.

The remaining three: `_render_ledger`, `_require_merge_driver_args`, and
`_union_evidence_`. `_union_evidence_` does not exist anywhere in the
tree at `bdb39bde3` (`git grep -n "def _union_evidence_"` -> no hits) --
naming drift in the original denominator prose (the real symbol is
`_union_evidence`, already among the 14 DETECTED), consistent with
attempt 1's evidence noting the same drift for other names. Not a real
miss; excluded from this attempt's target set.

## The real fix: `_walk_dead_ranges` never recursed into `with`/`async with`

`_require_merge_driver_args` is the syntactic (not constant-fold)
class-3 case attempts 1/2 already proved unsafe to fix without a
whole-repo call graph -- not reattempted here, same disposition as
those attempts' own conclusion.

`_render_ledger` traced to a genuine, narrowly-scoped constant-fold gap:
`_walk_dead_ranges`'s statement loop only recurses into an `ast.If`
node's own branches (`_fold_if_branch`) -- it has no case at all for
`ast.With`/`ast.AsyncWith`. This repo's actual `write_all`/`write_archive`
mode-dispatch (the real, non-synthetic shape) sits INSIDE a `with
ledger_lock(root):` block:

```python
with ledger_lock(root):
    mode = _store_mode(root)
    if mode == "single":
        ...
        return _write_all_single(root, tickets, digest)
    if mode == "v2":
        ...
    return _write_all_dir(root, tickets)
```

Confirmed empirically (not just by inspection) with a direct call to
`_dead_lines_by_file` against the unmodified detector: `write_archive`'s
OWN top-level `if _store_mode(root) == "v2": return ...` guard clause
folds fine (no `with` involved there), but `write_all`'s dispatch, one
`with` deep, produced ZERO dead lines in that range before the fix.
`with`/`async with` do not open a new variable scope in Python (unlike
`FunctionDef`/`ClassDef`, which correctly reset to `{}`), so recursing
into a `with` body with the CURRENT `local` map is sound -- not a new
analysis, the same fold logic already applied to a function's top-level
statement list.

## Result against the denominator

- `_render_ledger`: **still a miss even after the fix.** It has a
  genuinely live, unrelated caller: `migrate_to_ledger` (`_store.py`,
  called from the public `migrate()` in `_archive.py`, itself called
  from the public `frob.tickets.migrate` API) -- a legacy-directory-to-
  ledger collapse utility that is NOT gated by `_store_mode` at all, so
  its call to `_render_ledger` is not folded dead by ANY correct
  constant-fold analysis. `_render_ledger` is genuinely reachable at
  `bdb39bde3` through this one live path. T-1881's own evidence
  characterized this symbol as "dead: only reachable via whole-file
  write/read paths" without checking `migrate_to_ledger` specifically --
  this attempt's re-check suggests that characterization itself may be
  the thing that needs revisiting (a call graph question, not a
  constant-fold one), not something this fix can or should force.
- `_require_merge_driver_args`: unchanged miss, same class-3 cross-
  package cause attempts 1/2 already proved unsafe (no whole-repo call
  graph attempted here).
- Ratio against the 23-symbol denominator: **still 14/23** -- no new
  DENOMINATOR symbol newly detected, but the fix is NOT a no-op: it
  finds and correctly flags 4 new REAL dead symbols outside the
  denominator on the same repro tree (`_write_all_dir`,
  `_write_all_single`, `_dir_path_for`, `_prune_stale_files`), each
  hand-verified to have zero other live call sites in the package.

## Soundness check: zero new findings on the live tree (the check that sank attempts 1/2)

`timeout 540 uv run frob check --only dead_symbols` on this worktree's
CURRENT tree, before and after the fix (before = `git show HEAD:
src/frob/gates/_dead_symbols.py` swapped in temporarily, then restored):
**identical** in both cases -- `0 errors, 2 warnings, 42 waived`. No new
finding, no false positive, on the actual live repo (the `with`-wrapped
mode-dispatch shape this fix targets does not currently exist on `main`
-- it only existed transiently at `bdb39bde3`'s stage-1 snapshot).

Diff on the repro tree (`bdb39bde3`) before/after, full violation list:
exactly 4 additions (`_dir_path_for`, `_prune_stale_files`,
`_write_all_dir`, `_write_all_single`), 0 removals, 0 changes to any
other finding.

## Disposition

LANDED (not reverted): a real, narrowly-scoped, verified-safe fix, but
it does NOT move the ticket's own denominator ratio (still 14/23) --
`_render_ledger`'s miss was mischaracterized by earlier evidence as a
constant-fold gap when it is, in fact, a genuinely live symbol via an
unrelated call path. Filed as residue for whoever wants to re-verify
`_render_ledger`'s true reachability against a real (not per-package)
call graph, since `migrate_to_ledger`'s own liveness in a `_store_mode`-
collapsed world is itself questionable and outside this ticket's scope
to judge.

## Final characterization of all 9 (per-symbol, not collapsed)

| Symbol | Disposition |
|---|---|
| `_carry_forward_new_worktree_tickets` | permanently exempt: own `frob:tests` edge |
| `_carry_forward_or_refuse_sibling_edits` | permanently exempt: own `frob:tests` edges |
| `_newer` | permanently exempt: own `frob:invariant`+`frob:tests` edges |
| `splice_ledger` | permanently exempt: own `frob:tests` edge |
| `_archived_ids_for_merge_driver` | permanently exempt: own `frob:tests` edges (also class-3 syntactic, moot) |
| `_squash_and_splice_ledger` | permanently exempt: own `frob:tests` edge |
| `_render_ledger` | NOT provably dead: genuinely live via `migrate_to_ledger` (needs re-verification, not a detector gap) |
| `_require_merge_driver_args` | class-3 syntactic dead-caller, cross-package, unsafe without a whole-repo call graph (attempts 1/2's conclusion, unchanged) |
| `_union_evidence_` | not a real symbol at this commit (naming drift in the original denominator prose; the real name, `_union_evidence`, is already among the 14 DETECTED) |

Ratio: 14/23, unchanged. Zero of the 9 named misses are actually
closeable by ANY sound DEAD001 change as currently scoped -- 6 are
permanently exempt by design, 1 needs an unsafe cross-package call
graph, 1 is not actually dead, and 1 does not exist. This is the
honest ceiling for this detector shape against this denominator.
