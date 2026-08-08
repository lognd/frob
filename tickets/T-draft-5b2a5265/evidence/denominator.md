# T-1552 stage-1 detector-coverage measurement: methodology + raw denominator

Companion evidence to the ticket body -- this file is the primitive
record; the ticket body's prose is a claim ABOUT this data.

## Method

1. Captured `frob check --json` on `main` BEFORE any stage-1 change
   (baseline, not included here -- the delta is what matters).
2. Made exactly two changes, both real code, both committed
   (`bdb39bde3`, "wip(T-1552): stage-1 unwire v1 ledger splice
   machinery"):
   - `frob.tickets._store._store_mode` collapsed from a 4-way branch
     (`"v2"`/`"single"`/`"dir"`/`"v2"`) to unconditionally `return "v2"`.
   - The `"merge-driver"` CLI dispatch entry (`frob.app.ticket_runner`'s
     command table) and its argparse registration call deleted outright.
3. Immediately captured `frob check --json` again ->
   `stage1-frob-check.json` in this directory (1,207,713 bytes, 45 tool
   results, captured 2026-08-08).
4. Defined the 13-symbol denominator below BEFORE searching the capture
   (not post-hoc curve-fitted to whatever the gates happened to report).
5. Searched every `DEAD001`/`WIRE001`/`REF002`/`OPAQUE001`/`COV003`
   diagnostic in the capture for a substring match against each symbol's
   name (case-insensitive, against both `message` and `file`).

## Denominator (13 symbols)

| # | Symbol | Module | Reachability change |
|---|--------|--------|---------------------|
| 1 | `splice_ledger` | `_land_ledger_merge.py` | dead: only reachable via #3/#4 below |
| 2 | `_render_ledger` | `_store.py` | dead: only reachable via v1 whole-file write/read paths |
| 3 | `_squash_and_splice_ledger` | `_land_squash.py` | dead: `if _store_mode(root) == "v2": _squash_and_splice_ledger_v2(...) else: _squash_and_splice_ledger(...)` -- else arm now unreachable |
| 4 | `_merge_main_into_worktree` | `_land_git_ops.py` | dead: same shape, `_land.py:3579`, `_merge_main_into_worktree_v2(...) if _store_mode(root) == "v2" else _merge_main_into_worktree(...)` |
| 5 | `_splice_and_stage` | `_land_git_ops.py` | dead: called only from #3/#4 |
| 6 | `_splice_only_ticket` | `_land_ledger_merge.py` | dead: called only from #5 |
| 7 | `_land_merge.py`'s `splice_ledger` re-export | `_land_merge.py` | dead: re-exports #1, itself unreachable once #1 is |
| 8 | `_land_ledger_merge.py` module surface (`_merge_ledger_tickets`, `_resolve_divergence`, `_drop_resurrected_ids`, `_preserve_sibling_done_reports`, `_carry_forward_or_refuse_sibling_edits`, `_resolve_one_sibling_edit`, `_carry_forward_new_worktree_tickets`, `_overlay_landed_ticket`, `_parse_splice_only_sides`) | `_land_ledger_merge.py` | dead: internal helpers of #1/#6, no other caller |
| 9 | `_newer`/`_newer_winner`/`_richness`/`_union_evidence`/`_union_acceptance` | `_land_ledger_merge.py` | dead: called only from #1's own splice resolution |
| 10 | LEDGERV1001 check body | `gates/_tickets_gate.py` | dead: its own `mode in ("single", "dir")` condition, same `_store_mode` constant-fold shape |
| 11 | `_require_merge_driver_args` | `app/ticket_runner/_land_cmd.py` | dead: called only from `_merge_driver`, itself CLI-dispatch-unreachable after the explicit deletion |
| 12 | `_archived_ids_for_merge_driver` | `app/ticket_runner/_land_cmd.py` | dead: same -- called only from `_merge_driver` |
| -- | `_add_ticket_merge_driver_parser` | `_cli_parsers/_ticket/_progress.py` | **DETECTED** (not part of the miss count) -- its call site was deleted outright, a syntactic change, not a branch-constant one |

12 of these (#1-12) are MISSES: zero DEAD001/WIRE001/REF002/OPAQUE001/
COV003 findings named any of them in the post-stage-1 capture. The one
symbol NOT sharing the branch-constant shape --
`_add_ticket_merge_driver_parser`, whose call site was literally deleted
-- IS correctly flagged (`DEAD001: ...::_add_ticket_merge_driver_parser
is a private symbol with no call-graph caller...`).

## Corrections this survey produced to T-1552's own plan

- **`_land_merge_zones.py` is NOT v1-only and must NOT be deleted.**
  `_UNION_ZONES`/`_zone_for_path`/`_resolve_union_zone_conflicts` are
  general-purpose merge-conflict auto-resolution for registered
  "union zones" (`frob.toml`'s `gates.severity` block,
  `src/frob/gates/__init__.py`'s known-gate-rules block,
  `docs/audits/*.md`) -- called from `_auto_resolve_out_of_scope_
  conflicts` in `_land_git_ops.py`, which runs on EVERY land regardless
  of ledger store mode. This file was named for deletion in the
  ticket's original plan; that was wrong.
- **`_land_merge.py` is NOT a pure v1 re-export shim.** Besides
  re-exporting `splice_ledger` (dead, #7 above), it also defines/re-
  exports `_commit_message`, `_validate_closeable`, `_has_drop_reason`,
  `_has_failure_log` -- all live, v2-relevant land machinery with real
  callers outside any `_store_mode` branch. Deleting the whole file, as
  the ticket's plan literally says, would break `frob ticket land`.
  Only the `splice_ledger` re-export is dead.
- **Scope is 13 files, not the ~9 originally declared** -- see the
  ticket body's own scope-correction note.

## Constant-folding vs. real dataflow (all 12 misses characterized)

Every one of the 12 missed symbols traces back to the SAME shallow
pattern, at one or two hops of removal, never more:

- A direct call-and-compare: `if _store_mode(root) == "v2": ... else:
  ...` (`_land.py:3579`'s `_merge_main_into_worktree` site).
- OR one local-variable hop within the SAME function: `v2_mode =
  _store_mode(root) == "v2"` followed later by `... if v2_mode else
  ...` (`_land_squash.py`'s `_squash_and_splice_ledger` site,
  `gates/_tickets_gate.py`'s LEDGERV1001 site).
- Every other symbol (#1, #2, #5, #6, #8, #9) is dead PURELY because its
  only caller is one of the two sites above -- ordinary transitive
  call-graph propagation once the guarding branch is known-dead, not a
  SEPARATE instance of the constant-folding problem.
- #11/#12 are dead via a DIFFERENT, syntactic mechanism (the CLI
  dispatch entry was deleted outright) -- not part of this
  characterization, and not missed by the detectors for the same
  reason as the rest (they were not checked because their only caller,
  `_merge_driver`, is itself dead by the syntactic route, which a
  literal call-graph walk CAN see once the dispatch-table entry is
  gone -- yet these two specifically were still MISSED, meaning even
  the syntactic case has a gap once the dead symbol is TWO calls deep
  from the deleted entry point, not one -- worth flagging as a second,
  narrower finding: DEAD001 appears to require the caller be gone at
  <=1 hop, not full transitive closure).

**Conclusion: none of the 12 misses requires real interprocedural
dataflow, alias analysis, or path-sensitivity.** Every one resolves with:
(a) recognize a callee whose ENTIRE body is a single unconditional
`return <literal>` with no parameter read (`_store_mode`'s new shape --
a purely syntactic, single-function check, no call-site context needed);
(b) fold any `<call>() == <literal>` comparison against that callee,
including through exactly one local-variable assignment in the same
function (ordinary intra-procedural constant propagation, a standard,
cheap analysis); (c) propagate "unreachable" through the ordinary call
graph the tools already build, for anything ONLY reachable via the
now-dead branch. Steps (a)+(b) are the novel piece and are both
LOCAL/INTRA-PROCEDURAL -- no cross-function dataflow, no aliasing, no
loop or recursion reasoning. This is a DAY-SCOPE fix, not a MONTH-SCOPE
one: a narrow pre-pass recognizing "single-`return`-literal function,
compared for equality, at the call site or one local-var hop away" would
have caught all 12.

The one exception worth flagging on its own: #11/#12
(`_require_merge_driver_args`/`_archived_ids_for_merge_driver`) were
missed via the SYNTACTIC route (their only caller's dispatch-table entry
was deleted, an ordinary call-graph fact, not a constant-fold one) yet
still went undetected -- this suggests DEAD001's call-graph walk may not
transitively propagate "caller is dead" more than one hop, which is a
separate, narrower defect from the constant-folding gap and worth its
own look if the day-scope fix above does not already happen to close it.
