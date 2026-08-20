---
id: T-2702
title: 'T-2690''s phantom-refile fix does not work: two more auto-filed recoveries
  from lands that contained it'
state: queued
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
- src/frob/gates/_fix_engine.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: TICK006 phantom-refile fix lives in _fix_engine.py's _resolve_via_git_rename/_tick006_try_resolve_without_filing
    plus _land_cmd.py's MergeTargetKnownIds root-threading; tests/test_gates.py is
    the existing home for the T-2690 controls
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: TICK006 phantom-refile fix lives in _fix_engine.py's _resolve_via_git_rename/_tick006_try_resolve_without_filing
    plus _land_cmd.py's MergeTargetKnownIds root-threading; tests/test_gates.py is
    the existing home for the T-2690 controls
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_gates.py
  reason: TICK006 phantom-refile fix lives in _fix_engine.py's _resolve_via_git_rename/_tick006_try_resolve_without_filing
    plus _land_cmd.py's MergeTargetKnownIds root-threading; tests/test_gates.py is
    the existing home for the T-2690 controls
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: TICK006 phantom-refile fix lives in _fix_engine.py's _resolve_via_git_rename/_tick006_try_resolve_without_filing
    plus _land_cmd.py's MergeTargetKnownIds root-threading; tests/test_gates.py is
    the existing home for the T-2690 controls
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: TICK006 phantom-refile fix lives in _fix_engine.py's _resolve_via_git_rename/_tick006_try_resolve_without_filing
    plus _land_cmd.py's MergeTargetKnownIds root-threading; tests/test_gates.py is
    the existing home for the T-2690 controls
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_gates.py
  reason: TICK006 phantom-refile fix lives in _fix_engine.py's _resolve_via_git_rename/_tick006_try_resolve_without_filing
    plus _land_cmd.py's MergeTargetKnownIds root-threading; tests/test_gates.py is
    the existing home for the T-2690 controls
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## T-2690's fix landed and the spam continued

T-2690 landed at `c94445ddd` (2026-08-19 22:32:24) claiming to stop
phantom-filing auto-recovery. Two more recovery tickets were auto-filed
AFTER it, by lands that PROVABLY CONTAINED the fix:

    T-2699  filed 23:04:31  by land 5acddd68b (T-2141)
    T-2701  filed 23:35:14  by land a8c8f3361 (T-2251)

    git merge-base --is-ancestor c94445ddd 5acddd68b  -> YES
    git merge-base --is-ancestor c94445ddd a8c8f3361  -> YES

So this is NOT a stale-worktree artifact. The fix was present and both
of its mechanisms failed in production.

## Both mechanisms failed, and each is independently checkable

T-2699 and T-2701 have BYTE-IDENTICAL titles:

    Recovered from T-2685's phantom TICK006 citation of T-draft-be1e79b5

1. `_find_exact_duplicate` should have caught the second one. Identical
   title AND the same cited draft. It did not fire.
2. `_resolve_via_git_rename` should have prevented BOTH. The draft
   `T-draft-be1e79b5` IS resolvable: its deletion commit is
   `a44f96e6061be5e09a31028b919bb1e19745223c`, and `git show -M
   --name-status a44f96e60` yields `R099 tickets/T-draft-be1e79b5/ticket.md
   -> tickets/T-2678/ticket.md`. That is the EXACT command and commit
   T-2690's own author used to justify dropping T-2689 for this same
   draft id. The resolver had everything it needed and still refiled.

These are also duplicates of the already-dropped T-2689, which cited the
same draft -- so the class now has 3 tickets for one resolved rename.

## Why the tests did not catch it

T-2690 shipped four unit tests including both-direction controls, and they
pass. The production path still misbehaves. Something about how the fix is
INVOKED on the real land path differs from how the tests invoke it --
candidate causes worth checking first:

- the `ticket_id` threading fix changed which Done report is scanned; the
  spawning ticket here is T-2685, NOT the landing ticket (T-2141/T-2251),
  so the citation may be reached through a path the scoping did not cover
- the resolver may not run at all in the land-path invocation
- the duplicate check may compare against a snapshot that does not yet
  contain the sibling filed moments earlier in the same run

Do NOT assume which. Instrument the real land path and observe.

## Required

A positive control that exercises the REAL land path, not just the
function under test. A unit test that passes while production re-files is
precisely the gap here -- the same shape as a fix verified only by a proxy.

## Positive controls, both directions

- a land whose Done report cites a RENAMED draft must file NOTHING
- a land whose Done report cites a GENUINELY lost draft must still recover
  or report it -- do not fix this by disabling recovery
- two lands in quick succession citing the same draft must produce at most
  one ticket

## Cleanup in scope

T-2699 and T-2701 both resolve to T-2678 by the rename above. Drop both
with the commit and resolved id cited, exactly as T-2689 was dropped.
Measure each; do not drop on the class rate.
