---
id: T-2629
title: 'frob ticket doable does not complete: rendering scans all 938 branches with
  a temp-file parse per directive'
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_query.py
evidence_scope:
- tests/unit/test_app_runners_doable_stale_lease.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_render_never_scans_branches_inline
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_no_unlanded_work_prints_nothing
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_unlanded_branch_is_summarized
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_second_call_within_ttl_reuses_the_cache_not_a_fresh_scan
designated_repro_test: tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_render_never_scans_branches_inline
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f94e4c6d0df1a2898b8b3e1e15026fc87a4687bb
---
## Measured

`uv run frob ticket doable` does not complete. Two runs, both killed:

    timeout 540  -> EXIT=124   (no output at all)
    timeout 300  -> EXIT=124   (earlier the same night)

This is the PRIMARY queue command. It is what the coordinator and every
agent use to answer "what should I work on", and it currently cannot
answer.

## Root cause, from a stack dump rather than a guess

`PYTHONFAULTHANDLER=1 timeout -s ABRT 90 uv run frob ticket doable`:

    _doable  (app/ticket_runner/_query.py:381)
      _render_doable_plain                          (_query.py:562)
        _render_unlanded_branch_work_summary        (_query.py:902)
          _unlanded_branch_work                     (_unlanded.py:704)
            _unlanded_findings_for_branch           (_unlanded.py:657)
              _finished_signals_on_branch           (_unlanded.py:409)
                _directive_anchor_signals_on_branch (_unlanded.py:605)
                  _directive_anchored_ticket_ids    (_unlanded.py:553)
                    _directive_ids_via_real_parser  (_unlanded.py:508)
                      tempfile.NamedTemporaryFile

So rendering `doable` triggers a full unlanded-branch-work scan, and that
scan writes a TEMP FILE and runs a real tree-sitter parse per directive
candidate.

Scale on this repo right now:

    branches:  938
    worktrees:  35

938 branches, each scanned, with a temp-file write + flush + full parse per
directive candidate. That is the runtime.

## Three separable problems -- decide which this ticket takes

1. **`doable` should not do this work inline at all.** A queue query
   should not depend on scanning every branch in the repository. Either
   drop the summary from the default render, compute it lazily behind an
   explicit flag, or serve it from cached state. This is the one that makes
   `doable` usable again and is the minimum fix.

2. **Parsing via a temp file is the wrong mechanism.** `_directive_ids_via_
   real_parser` writes `text` to a NamedTemporaryFile purely so `parse_file`
   has a path to open. That is a syscall-heavy round trip per candidate. If
   the parser can accept in-memory content, use it; if it genuinely cannot,
   that is worth its own ticket against `frob.lang`.

3. **938 branches is itself accumulated debt.** Most correspond to landed
   or abandoned agent work. Even a fast scan over 938 branches is wasted
   work. Pruning is related to T-2599/T-2617's worktree audit (35
   worktrees, currently 0 STRANDED) but branches outnumber worktrees ~27x,
   so it is a distinct cleanup. FILE THIS SEPARATELY rather than folding it
   in -- deleting branches is destructive and needs its own stranded-work
   analysis, exactly like the worktree audit did.

Prefer (1) alone for this ticket. It restores the command. (2) and (3)
should be filed and sized on their own.

## Do NOT

- Do NOT "fix" this by adding a timeout or a partial result that silently
  returns fewer tickets. A truncated doable list that looks complete is a
  silent zero, and this repo's dominant bug class. If the summary cannot be
  computed, say so in the output rather than omitting rows.
- Do NOT delete branches as part of this ticket.

## Positive controls, both directions

- `frob ticket doable` COMPLETES on this repo (938 branches, 35 worktrees)
  well within a normal command budget, and lists tickets
- the ticket set it returns is IDENTICAL to what the pre-fix code path
  returns on a small fixture repo where both can run to completion -- this
  is what proves the fix did not change WHICH tickets are doable, only how
  fast the answer arrives
- if the unlanded-branch-work summary is moved behind a flag or cache, the
  summary is still REACHABLE and still correct when requested
- a repo with zero branches beyond main still renders correctly