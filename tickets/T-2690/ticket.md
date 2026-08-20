---
id: T-2690
title: TICK006 phantom-filing auto-recovery is 92% false-positive and its refusal
  blocks unrelated lands
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
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: 'TICK006 Tier-A phantom-citation recovery lives entirely in _fix_engine.py:
    scope-narrow to ticket_id (already threaded per T-1548), resolve via git rename
    before filing, dedupe against an existing recovery ticket before re-filing'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_gates.py
  reason: 'TICK006 Tier-A phantom-citation recovery lives entirely in _fix_engine.py:
    scope-narrow to ticket_id (already threaded per T-1548), resolve via git rename
    before filing, dedupe against an existing recovery ticket before re-filing'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/gates.md
  reason: documenting the fix under the existing TICK006 Tier-A section
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_tick006_renamed_draft_resolved_via_git_not_refiled
- tests/test_gates.py::TestFixEngineTierA::test_tick006_already_recovered_citation_rewritten_not_refiled_again
- tests/test_gates.py::TestFixEngineTierA::test_tick006_ticket_id_scopes_to_landing_ticket_only
- tests/test_gates.py::TestFixEngineTierA::test_tick006_genuinely_lost_draft_still_caught_no_rename_no_duplicate
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured

25 tickets have ever been auto-filed with the title shape
"Recovered from T-XXXX's phantom TICK006 citation of T-draft-XXXXXXXX".

    dropped   23
    queued     2  (T-2687, T-2689 -- filed today, not yet triaged)
    ---------------
    false-positive rate  23/23 triaged = 100%; 92% of all 25

Every single one that has been triaged was dropped as a bookkeeping
duplicate of already-completed or already-tracked work. Four were
triaged today (T-2590, T-2601, T-2657, T-2658): in each case the cited
draft was genuinely filed on a parent's worktree branch and never merged
when that parent landed, and the described work already existed on main
under a real id. Nothing was ever lost -- only double-tracked.

## Mechanism

The TICK006 Tier-A auto-fix (T-1544) treats a stale pre-renumber draft
citation on a worktree branch as a "phantom filing" and auto-recovers it
by spawning a new ticket. Drafts renumber on land, so ANY branch holding
a pre-land citation looks phantom to it.

Observed directly today: T-2687 was spawned as a garbled duplicate of the
real T-2684 -- truncated body starting mid-sentence -- from a worktree
branch's own stale citation, while T-2684 itself was fine and already
fixed.

## Second, worse effect: it blocks unrelated lands

The same mechanism fires during other tickets' pre-land Tier-A pass and
produces

    refusing to file "<title>" -- T-draft-XXXXXXXX already has this
    exact title and this exact scope

Today that refusal blocked one agent's land for 45 minutes. It is
indistinguishable from lock contention if you watch elapsed time rather
than read the error, and I misattributed it to contention and serialised
the whole fleet before finding the real cause. It presents as a
non-fatal WARNING inside the Tier-A fixer in some paths and as a hard
refusal in others, which is itself worth reconciling.

## Required shape

An auto-recovery that is wrong 92% of the time is not a safety net, it
is a spam generator, and its output is indistinguishable from real work
until a human or agent burns time triaging it. Either:

- do not treat an unmerged draft citation on a worktree branch as
  phantom at all (the branch is the expected home of a pre-land draft), or
- resolve the citation through the renumber map before deciding, so a
  draft that became a real id is recognised rather than re-filed, or
- if recovery must stay, it must not FILE. Report the suspected loss and
  let a human or agent confirm before a ticket exists.

## Positive controls, both directions

- a draft that was genuinely lost (filed on a branch, parent landed, work
  absent from main) must STILL be recoverable/reported -- without this the
  fix is indistinguishable from deleting the feature
- a draft that merely renumbered on land, or that is still live on an
  unlanded branch, must NOT spawn a ticket
- the pre-land Tier-A pass must not emit the duplicate-title refusal for
  a ticket unrelated to the citation

## Notes

Triage the 2 outstanding (T-2687, T-2689) as part of this. Expect both to
be drops, but MEASURE -- do not drop on the class rate alone. A drop is
terminal and this repo has previously auto-dropped live findings by
reasoning from shape instead of measurement.