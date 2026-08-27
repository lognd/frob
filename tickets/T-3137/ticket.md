---
id: T-3137
title: frob ticket fail from a worktree never reaches main and does not say so
state: in-progress
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Record the measured mirror asymmetry between fail and promote, and that
    the fleet has survived it by workflow accident
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3180
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FOUND 2026-08-27 by an agent that had already landed its ticket and then needed
to record a failure for a SECOND ticket in the same series.

`frob ticket fail` and `frob ticket new`, run from inside a WORKTREE,
auto-commit onto the WORKTREE BRANCH ONLY. They do not reach main. If no
further land carries that branch -- which is exactly the situation once the
series' landing ticket is already done -- the failure log and the new ticket are
INVISIBLE TO THE FLEET and are lost when the worktree is swept.

The asymmetry that makes this a trap rather than a known constraint:
`frob ticket promote` SELF-MIRRORS to main and SAYS SO in its output.
`frob ticket fail` does not mirror, and its output gives NO HINT that what it
just recorded is invisible. A caller reasonably reads a successful-looking
`fail` as "the dead end is now on the record". It is not.

WHY THIS MATTERS MORE THAN IT LOOKS. `frob ticket fail` is the SANCTIONED way
to record a dead end -- the house rule is explicitly "use `fail`, never `drop`,
so the dead end is recorded". So the one verb agents are instructed to reach
for when work cannot proceed is the one whose record can silently fail to
reach the fleet. The next agent dispatched against that ticket then repeats the
dead end, because the reason it failed is sitting on a deleted branch.

MEASURED CONTEXT, both directions:
- The trap is real: the reporting agent hit it directly and had to re-run with
  `frob ticket fail --path <root>` and use `frob ticket promote` for the draft.
- It has NOT silently eaten records in practice so far: I checked T-3086, which
  has been failed five separate times by five agents, and all six failure-log
  entries ARE present on main. Those agents happened to land ticket-only
  commits afterwards (`frob ticket land --plan`), which carried them. So the
  current fleet survives this by accident of workflow, not by design.

WHAT IS WANTED
- `frob ticket fail` from a worktree should either mirror to main the way
  `promote` does, or say LOUDLY that it has not, naming the exact follow-up
  (`--path <root>`, or the land that will carry it). Silence is the defect.
- Audit the other ticket verbs for the same asymmetry. `promote` mirrors and
  announces; `fail` does neither. `new`, `block`, `unblock`, `scope`, `body`,
  `evidence` and `done-report` should each be checked and the results
  reported -- some mirror (I have observed `scope --add` mirroring from a
  worktree), some may not, and nobody has enumerated which.
- Whatever the fix, the OUTPUT must make the reachability state obvious. This
  repo's recurring failure is the silent zero -- a result that looks like
  success because the thing that would have reported failure never ran or never
  arrived.

ACCEPTANCE
- `frob ticket fail` run from a worktree either reaches main or reports plainly
  that it has not, naming the follow-up. Must-fire fixture from a real worktree.
- The same call from the root is unchanged. Must-stay-quiet fixture.
- The per-verb mirror audit is reported as a table: verb, mirrors yes/no,
  announces yes/no.
- No verb ends in a state where a caller can reasonably believe a record
  reached the fleet when it did not.
