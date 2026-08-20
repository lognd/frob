---
id: T-2742
title: 'No reliable way to detect an in-flight land: every hand-rolled pgrep matches
  the polling shells themselves'
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'correct the ticket''s premise: fleet_status already reports LANDS IN FLIGHT,
    so this is a discoverability and documentation fix, not a build'
  actor: logan
  at: '2026-08-20'
  old_length: 3083
  new_length: 4901
- mode: append
  reason: record why this ticket tripped DOC006 and disclose that its hypothetical
    verb name is prose, not a command
  actor: logan
  at: '2026-08-20'
  old_length: 4901
  new_length: 5592
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## The problem

There is no reliable way to ask "is a land in flight right now?". Every
agent hand-rolls a `pgrep`, and every hand-rolled form is wrong in the
same way: the polling shell's OWN command text contains the pattern it is
searching for, so it matches itself -- and, since all agents share a
session, it matches every OTHER agent's poller too.

Measured 2026-08-20 with one genuine land running:

    pgrep -f "bin/frob ticket land"                          -> 4 matches, 1 real
    pgrep -f "worktrees/.*/.venv/bin/frob ticket land"       -> 4 matches, 1 real
    pgrep -af "^/.../worktrees/[^/]*/.venv/bin/python "      -> 1 match,  1 real

The three extra matches were `/bin/bash -c ... pgrep -f "..." ...`
processes at 0.0% CPU -- other agents' wait loops.

## Cost, measured

This has produced wrong conclusions in FIVE separate contexts in one
session:
- one agent parked FOUR consecutive times waiting for a count that could
  never reach zero, because its own poller kept the count above zero; its
  finished ticket had to be landed by the coordinator
- another agent stalled on the same condition and reported a false
  premise ("frob ticket work needs the land lock free" -- it does not)
- the coordinator twice read a healthy fleet as busy, and once killed a
  stray watcher of its own that was inflating the count
- a "3 concurrent lands" reading that drove a fleet-wide serialisation
  decision was partly this artifact

The workaround (anchor the match at the start of the cmdline, or read
`/proc/<pid>/exe`) is not discoverable, and each agent rediscovers the
bug rather than the fix.

## What to build

A first-class query -- e.g. `frob land status` or a field on the existing
fleet status -- that answers, authoritatively:
  - how many lands are genuinely in flight
  - which ticket and worktree each belongs to
  - how long each has been running

It must identify a land by something structural (the land lock's recorded
pid, the process's real executable, or a land-owned marker file), NOT by
matching text in a cmdline. Note `.frob/land.lock` already records a
holder pid -- reading it and checking liveness may be most of the answer,
but verify it covers the pre-lock window before relying on it alone.

Then update `docs/guides/agent-playbook.md` to point at that command, and
remove the hand-rolled pgrep guidance wherever it appears -- including in
my own dispatch briefs, which have been propagating the broken form.

## Positive controls, both directions

- with N genuine lands running and M agents polling, the command reports
  exactly N, for N in {0,1,2} and M > 0
- the command does not count itself
- a land that has died leaves no phantom entry (check a killed land, not
  just a completed one)

## Related

`frob ticket land` already refuses correctly when the lock is held, so the
enforcement path is fine. This is purely about OBSERVABILITY -- agents
cannot see what the tool already knows, so they guess, and the guess is
systematically wrong. Same shape as T-2141's carried-changeset disclosure
and T-2737's pollable-progress request.




## CORRECTION (coordinator, same day): the capability ALREADY EXISTS

I filed this as 'build a first-class query'. That was wrong. `scripts/fleet_status.py` already reports it, authoritatively and correctly:

    ROOT CLEAN
    LANDS IN FLIGHT: 1
    LAND LOCK: file exists, no live holder -- normal resting state (flock
      releases instantly on holder death; the recorded pid may be reused,
      do not trust it or lock age)

It even carries the warning about not trusting the lock's recorded pid --
the exact trap I was about to send an implementer into by suggesting they
read `.frob/land.lock`.

So this ticket is NOT 'build the query'. Do not build a second one. It is:

1. SURFACE IT. Every agent, and I, reached for a hand-rolled `pgrep`
   instead. That is a discoverability failure, not a missing feature.
   Find why: check whether `docs/guides/agent-playbook.md` recommends a
   pgrep form, and correct it to point at fleet_status.
2. REMOVE THE BROKEN GUIDANCE wherever it appears. My own dispatch briefs
   propagated two successive wrong pgrep patterns, and the repo's own
   `frob-suggest` hook already nudges toward fleet_status -- the guidance
   and the tooling disagree.
3. Only if fleet_status's own count proves unreliable under load should
   any code change follow, and that needs measurement first.

The measured evidence in this ticket body still stands and is still the
justification: 4 pgrep matches vs 1 real land, and five wrong conclusions
in one session. The remedy is different from what I first wrote.

This is an instance of a pattern worth naming: a capability that ships
but is not reachable from where people look is functionally absent, and
gets rebuilt or worked around. Check whether the thing exists before
building it -- I did not, and nearly commissioned a duplicate.



## DOC006 note (coordinator)

This ticket's own body originally proposed a hypothetical verb inside a
backtick code span. DOC006 correctly read that as a live CLI invocation
that does not resolve, fired, and the resulting quarantine blocked
deferred landing repo-wide until it was disposed -- a ticket about
observability degrading the fleet through its own prose.

Treat any verb name in this body as PROSE, not a command. The proposal is
a first-class land-status query; per the correction above, the capability
already exists in scripts/fleet_status.py, so no new verb should be
minted at all. Same shape as T-2691, which was resolved by moving a
future-verb mention out of backticks.