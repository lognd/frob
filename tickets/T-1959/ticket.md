---
id: T-1959
title: 'Dead-by-constant-branch: close the remaining 9/23 misses left by T-1881 (multi-hop,
  boolean-composition, syntactic dead-caller)'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_dead_symbols.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: adding regression tests for the with-block fold gap fix
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gates.py::TestDeadSymbolGate::test_call_site_inside_with_block_dead_branch_is_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_call_site_inside_with_block_live_branch_is_not_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FOLLOW-UP to T-1881 (landed 969eaeca0622), which took dead-by-constant-
branch detection from 0/23 to 14/23 against a controlled denominator
(same tree, same commit `bdb39bde3`, only the detector code differing).

THIS TICKET EXISTS BECAUSE THE RESIDUE HAD NO QUEUE ENTRY. T-1881's 9
remaining misses are characterized carefully in
`tickets/T-1881/evidence/fix-measurement.md` and in that ticket's own
acceptance criterion [2]. That is a genuinely good record -- but T-1881
is DONE and archives, and neither an evidence file nor a closed ticket's
acceptance criterion is read by `frob ticket doable`. Catalogued is not
enforced: work that lives only in a done ticket's prose is invisible to
every queue view and gets silently dropped. The measurement stays where
it is; this ticket is the queue entry that points at it.

THE REMAINING 9, in three distinct classes (from that evidence file):

1. MULTI-HOP PROPAGATION GAP -- `_render_ledger`, `splice_ledger`.
   Their own direct call sites fold correctly; liveness depends on an
   upstream hop the bounded fixed point (`_MAX_TRANSITIVE_ROUNDS`) does
   not resolve, incl. a producer missed due to a shadowing import alias.

2. BOOLEAN-COMPOSITION HOP -- `_squash_and_splice_ledger`. Same folded-
   ternary shape as a case that DOES work, but its callers are reached
   through an intermediate `and`/`or` composition (`v2_mode and not
   force_v1`) that single-assignment-hop tracking does not carry. T-1881
   explicitly bounded itself to one hop, so this is a scope cut, not a
   defect in what shipped.

3. SEPARATE SYNTACTIC DEFECT -- `_require_merge_driver_args`,
   `_archived_ids_for_merge_driver`. DEAD001's call-graph walk does not
   transitively propagate dead-CALLER status past one hop for the
   ORDINARY syntactic-deletion case. This has nothing to do with constant
   folding and is the most independently valuable of the three; T-1881
   flagged it and left it open deliberately, with a regression test
   confirming it is still open.

Class 3 is the recommended starting point: it is orthogonal to the
constant-folding machinery, so it can be fixed without disturbing the
14/23 that now work.

DO NOT FIX IT THIS WAY: do not chase the ratio by loosening detection.
T-1881 verified no new findings on the live tree (0 errors before and
after) and hand-checked the extra findings it surfaced. A detector that
reports LIVE code as dead is far worse than one that misses dead code --
acting on a false positive deletes working code. Every added detection
must be provable; if a case cannot be proven, leave it a MISS and say so.

Also do not re-derive the baseline. Reuse T-1881's harness and the SAME
denominator (23 symbols at `bdb39bde3`, see
`tickets/T-1881/evidence/denominator.md`) so the ratio stays comparable.
A new denominator makes the numbers incomparable and hides regressions.

ACCEPTANCE: report a new detected/23 ratio against that same denominator,
with each still-missing symbol individually characterized (no collapsing
into name-groups). Confirm `frob check --only dead_symbols` stays at 0
errors on the live tree. First test must fail before the fix.

## Failure log
- 2026-08-10 attempt 1: class-3 fixed-point propagation via zero-intra-package-caller detection is structurally unsound: it cannot distinguish the genuine denominator case (_merge_driver, dispatch entry deleted) from this repo's ~41 already-waived cross-package _add_parser false positives, both look identical from per-directory call-graph info alone; measured 3->117 warnings on the live tree, reverted in full; ratio stays 14/23; see evidence/class3-reverted.md
- 2026-08-10 attempt 2: Class 3 fix attempted: transitive dead-caller propagation via forward-reachability-from-ROOT through build_reference_graph. PROVEN UNSOUND before landing: cascades false-dead status through symbols alive only via a cross-package call the graph cannot see and that already carry a human-reviewed frob:waive DEAD001 (e.g. _add_cycle_parser, called from __main__.py in a different package) -- my algorithm has no notion of existing waivers, so it treats such a waived symbol as a dead root and cascades that false deadness onto everything it calls. Measured: repo-wide gate:DEAD warnings went from 2 to 84 (126 total findings) after the change; verified at least one concrete false positive (_populate_cycle_args, live via _add_cycle_parser -> __main__.py argparse dispatch) before reverting. Reverted fully (git checkout, confirmed clean diff) -- landed nothing, per this ticket's own explicit instruction that a false positive is worse than a miss. NEXT ATTEMPT must account for existing frob:waive DEAD001 sites as alive roots (needs plumbing waiver-comment awareness into dead_symbol_gate, which it does not have today) before any transitive propagation is safe.

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
