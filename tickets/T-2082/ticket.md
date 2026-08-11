---
id: T-2082
title: PassengerTickets false-refuses every refactor that relocates a pre-existing
  frob:ticket directive, training agents to reflex --allow-cross-ticket
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given a branch that only RELOCATES an existing frob:ticket directive to a
    new line in the same file (net occurrence delta zero), when frob ticket land runs,
    then it does NOT refuse with PassengerTickets and no --allow-cross-ticket is needed
    -- this test MUST fail against current main
  evidence: []
- text: given a branch that genuinely ADDS a new frob:ticket directive naming another
    ticket (the T-1618 incident shape, passenger code physically present), when frob
    ticket land runs, then it still refuses with PassengerTickets and names that id
    -- proving the guard is not weakened
  evidence: []
- text: given the passenger ticket record reads DONE or DROPPED, when its code is
    genuinely added by the landing branch, then the refusal still fires -- the ledger-state-blind
    property of the check is preserved
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
---
## Measured evidence: two independent agents, same false refusal, same hour

Both were pure ARCH001 refactor splits that extracted helper functions and
carried the ORIGINAL function's pre-existing `frob:ticket` attribution
comments to the new call sites. Neither added a single line of the named
tickets' code.

1. **T-2073** (`_query.py`, splitting `_doable`): refused with
   `PassengerTickets` naming FOUR ids -- T-0715, T-0752, T-0972, T-2006 --
   all pre-existing directive comments relocated onto the new split-out
   helpers. The agent verified with `git diff main...HEAD --stat` that the
   whole changeset was only `_query.py` plus T-2073's own ticket files, then
   landed with `--allow-cross-ticket`.

2. **T-2077** (`_rapid_sweep.py`, splitting `_file_regression_ticket` and
   `run_deferred_post_land_sweep`): refused with `PassengerTickets` because
   the extracted `_resolve_regression_attribution` carries a pre-existing
   `# frob:ticket T-2009` comment. Agent's words: "documentation only, not
   new T-2009 code -- confirmed via `git diff main...HEAD --stat` showing
   only my own files". Landed with `--allow-cross-ticket`.

## Root cause, read from the source (not inferred)

`_directive_ticket_ids_in_diff` (`src/frob/tickets/_land.py`) collects ids
from ADDED lines only:

    for line in diffed.danger_ok.stdout.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        found.update(_DIRECTIVE_TICKET_ID_RE.findall(line))

Its docstring is explicit that this is deliberate: "`frob:ticket <id>`
directive ADDED (`+`-prefixed source line, never a context/removed line)".

Nothing in the scan asks whether the SAME directive was removed elsewhere in
the same diff. A refactor that relocates a function emits
`+ # frob:ticket T-2009` at the new site and `- # frob:ticket T-2009` at the
old -- a net change of ZERO occurrences -- and the guard counts the addition
and refuses.

## Why this costs more than the two retries

It trains agents to reach for `--allow-cross-ticket` as routine. That flag is
a genuine safety override, and this repo has already paid for it twice: the
2026-08-05 incident where landing T-1581 out of a shared worktree carried
T-1579's WAIVE004 change onto main and deleted 55 live `frob:waive`
directives across five gate families; and the passenger-land-order trap,
where carrying a sibling's FIX to main first strands that sibling in BUG002
permanently because its repro can no longer fail at its parent. A guard that
cries wolf on ordinary refactors is a guard whose override becomes reflex.
The repo is currently doing many ARCH001 splits, so the false-positive rate
is rising, not incidental.

## THE DISCRIMINATOR

Compare each id's OCCURRENCE COUNT at `base_ref` versus `HEAD`. Only ids
whose count INCREASED are genuine passengers. A pure move nets zero.

This does NOT weaken the T-1618 guard, and that must be verified rather than
asserted: in the 55-waiver incident the passenger's code was physically ADDED
to the landing branch, so its directive count strictly increased and a
count-based check still refuses. Add a regression test that reproduces that
incident's shape and confirm it still refuses after the change.

## DO NOT FIX IT THIS WAY

- **Do not exempt ids that merely already exist somewhere at `base_ref`.**
  That is the tempting one-line version and it is unsound: a genuine
  passenger usually names a ticket that already has directives elsewhere in
  the tree. Existence at base is not the question; the DELTA is.
- **Do not consult the passenger ticket's ledger state.** The docstring is
  emphatic that ignoring ledger state is the point, not an oversight -- the
  T-1618 incident is exactly a sibling whose ledger said DONE/DROPPED while
  its code rode along. Do not re-introduce that exemption.
- **Do not widen `--allow-cross-ticket` or add a second override flag.** The
  two existing checks deliberately share ONE flag so a caller has only one
  concept to learn. Another override makes the reflex worse.
- **Do not switch to `--name-only`.** The check needs hunk CONTENT; a
  `frob:ticket` directive is a source line, not a path.
- **Do not silence the refusal into a warning.** Its loudness is what made
  both agents stop and verify. Keep it loud; make it CORRECT.

## A case to decide explicitly, not by accident

A passenger that MOVES existing code and also MODIFIES it nets zero
occurrences while genuinely changing behaviour. Decide whether a
count-unchanged id must also require that the removed and added directive
lines correspond to a pure relocation, and say which you chose and why. Err
toward refusing when ambiguous: a false refusal costs one flag, a false pass
costs an incident.
