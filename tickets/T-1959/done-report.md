## Done report

Changed: `_walk_dead_ranges` in `src/frob/gates/_dead_symbols.py` (new
`_TRANSPARENT_BLOCK_KINDS` recursion into `ast.With`/`ast.AsyncWith`
bodies, same `local` map, no new scope). Two new regression tests in
`tests/test_gates.py::TestDeadSymbolGate`.

Evidence: `tests/test_gates.py::TestDeadSymbolGate::test_call_site_inside_with_block_dead_branch_is_flagged`,
`tests/test_gates.py::TestDeadSymbolGate::test_call_site_inside_with_block_live_branch_is_not_flagged`
(the false-positive guard). `--check-repro` returns NO_VERDICT (both are
brand-new test nodes, cannot collect at parent) -- manually confirmed
before committing: the dead-branch test fails with `AssertionError:
assert False` against the unmodified detector (0 violations found), and
passes after the fix. Same disclosed-NO_VERDICT shape T-1881's own Done
report used for its new-node regression tests.

Full detail: `tickets/T-1959/evidence/attempt3-with-block-fix.md`.

## Summary

Two prior attempts on this ticket (both reverted, see the ticket's
Failure log) tried to generalize dead-CALLER propagation across the
whole call graph and both caused a false-positive explosion (2->84 and
0->114 warnings) because `build_reference_graph` is per-package only and
cannot distinguish a genuinely-deleted caller from this repo's ~41
already-waived cross-package dispatch cases. This attempt did NOT repeat
that approach.

Before writing any code, all 9 named misses were checked against
DEAD001's own DECLARED-reference exemption (`frob:tests`/`frob:invariant`
directly on the symbol). **6 of the 9 carry that exemption directly**:
`_carry_forward_new_worktree_tickets`, `_carry_forward_or_refuse_sibling_edits`,
`_newer`, `splice_ledger`, `_archived_ids_for_merge_driver`,
`_squash_and_splice_ledger`. These are permanently unclosable by any
correct DEAD001 change without weakening the exemption itself -- which
the ticket explicitly forbids ("do not chase the ratio by loosening
detection"). Neither T-1881 nor the two prior attempts identified this;
both treated all 9 as open detection gaps. This changes the honest
ceiling for this ticket's own denominator from 9 open misses to at most
3.

Of the remaining 3: `_union_evidence_` does not exist at the denominator
commit (naming drift -- the real symbol, `_union_evidence`, is already
among the 14 DETECTED). `_require_merge_driver_args` is the class-3
syntactic dead-caller case the two prior attempts already proved unsafe
to fix without a whole-repo call graph -- not reattempted. `_render_ledger`
traced to a real, narrow, previously-uncharacterized bug:
`_walk_dead_ranges` only ever recursed into `ast.If` branches, never
into `ast.With`/`ast.AsyncWith` -- so this repo's actual `write_all`/
`write_archive` mode-dispatch, which sits one `with ledger_lock(root):`
block deep, was completely invisible to the constant-fold pass. Fixed
(with/async-with is transparent to Python's variable scoping, so
recursing with the current `local` map is sound -- no new fold logic,
same mechanism already used for a function's own top-level statements).

**Result: the fix is real, tested, and verified safe, but does not move
the ticket's own 14/23 ratio.** After the fix, `_render_ledger` is STILL
a miss -- not because the fix failed, but because `_render_ledger` has a
genuinely live, unrelated caller (`migrate_to_ledger`, a legacy-
directory-collapse utility not gated by `_store_mode` at all) that T-1881's
own evidence did not check for. It is not actually provably dead by any
correct analysis at this commit; the original "still MISSED" classification
appears to be the thing that needs re-examining, not the detector.

The fix is not a no-op, though: measured on the same `bdb39bde3` repro
tree, it correctly newly detects 4 REAL dead symbols outside the
23-symbol denominator (`_write_all_dir`, `_write_all_single`,
`_dir_path_for`, `_prune_stale_files`), each hand-verified to have zero
other live call sites. Verified ZERO new findings and zero regressions
on the actual live tree (`frob check --only dead_symbols`, identical
`0 errors, 2 warnings, 42 waived` before and after, swapping the file
content back and forth in place). Full `tests/test_gates.py` suite
(710 tests) passes.

Ratio against the T-1881 denominator: **14/23, unchanged.** Final
per-symbol characterization of all 9 original misses (table in the
evidence file): 6 permanently exempt by design, 1 not actually dead
(needs re-verification, not a fix), 1 needs an unsafe whole-repo call
graph (unattempted, same conclusion as attempts 1/2), 1 does not exist.
This is the honest, fully-characterized ceiling for this detector shape
against this denominator -- no further ratio movement is achievable
without either weakening the declared-reference exemption (forbidden by
this ticket's own instruction) or building the whole-repo call graph
the module's own docstring already documents as a deliberate,
out-of-scope architectural bound.

Filed: none. (The `_render_ledger` re-verification question and the
whole-repo call graph need are both already characterized in this
ticket's own body/evidence rather than left as a new, undiscoverable
residue -- no new ticket needed beyond what a future dispatcher can read
directly here.)

Gates: `frob check --only dead_symbols` clean (0 errors, 2 warnings,
42 waived, unchanged before/after this change). Full `tests/test_gates.py`
suite green (710/710).

### Changed
```
 src/frob/gates/_dead_symbols.py                    |  20 ++-
 tests/test_gates.py                                |  76 ++++++++++
 tickets/T-1959/evidence/attempt3-with-block-fix.md | 163 +++++++++++++++++++++
 tickets/T-1959/ticket.md                           |  12 +-
 4 files changed, 269 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDeadSymbolGate::test_call_site_inside_with_block_dead_branch_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_call_site_inside_with_block_live_branch_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, F401@/home/logan/projects/frob/.claude/worktrees/t1959-t2016/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1959-t2016/tests/unit/test_tickets_evidence_only_scope.py
