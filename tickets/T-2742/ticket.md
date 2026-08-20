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
