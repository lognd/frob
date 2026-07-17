---
name: next
description: The main work loop -- frob ticket doable, pick the top item, dispatch implementer, have reviewer verify, close, repeat until the queue is empty or blocked. Use to work down an existing ticket queue.
---

# next

Pop, implement, verify, close. Repeat. This is the loop that turns a ticket
tree from `plan` into finished, evidenced work.

## The loop

```bash
frob ticket doable                 # ordered, unblocked, oldest-first
```

For each pass:

1. **Pick** the top ticket from `frob ticket doable`. Do not skip ahead to a
   ticket you find more interesting -- ordering exists so nothing rots at
   the bottom of the queue.
2. **Dispatch** the `implementer` agent with that ticket's id. It runs
   `frob ticket start`, implements within scope, records evidence, and
   writes the Done report -- but does not close the ticket itself in a
   review-gated workflow; wait for its report.
3. **Verify** by dispatching the `reviewer` agent against the same ticket
   id. It checks the Done report against the real diff and evidence and
   returns APPROVE or REJECT.
4. **Close or return**:
   - APPROVE: `frob ticket close T-00xx` (if implementer hasn't already).
   - REJECT: hand the reviewer's findings back to a fresh `implementer`
     dispatch on the same ticket. Do not close over a REJECT.
5. **Repeat** with the next `frob ticket doable` call -- re-query every
   pass, since closing one ticket can unblock others.

## Stopping conditions

- **Queue empty**: `frob ticket doable` returns nothing and `frob ticket
  list` shows no `queued`/`planned` tickets left un-blocked. Done.
- **Everything left is blocked**: `frob ticket doable` is empty but
  `frob ticket list` shows open `blocked` tickets. Surface these to the
  human -- do not force an ordering or invent a resolution.
- **A ticket fails repeatedly**: if `implementer` or `debugger` records a
  `frob ticket fail` entry twice for the same ticket, stop looping on it
  and surface it to the human instead of retrying a third time.

## When a ticket blocks mid-implementation

If `implementer` reports it cannot proceed (missing prerequisite, wrong
assumption in the plan), it will have run `frob ticket block T-00xx --by
T-000Y` or `frob ticket fail T-00xx "..."`. Move on to the next doable
ticket in this same loop pass -- do not stall the whole queue on one item.

## Surfacing blockers

At the end of any pass that stops before the queue is empty, report:

```
Queue status: N done this pass, M still queued, K blocked

Blocked:
- T-0044 blocked_by=[T-0041] "..." -- T-0041 still in-progress
- T-0047 failed twice: "wl-paste backend; no wayland socket in WSL"
```

## Hard rules

- Never implement directly in this skill -- always through the
  `implementer` agent, so scope discipline and evidence recording happen
  the same way every time.
- Never close a ticket the reviewer rejected.
- Never reorder the queue by hand-picking a ticket other than the top of
  `frob ticket doable`, except to skip one already known to be blocked or
  repeatedly failed (and even then, say so explicitly in the output).
- Re-run `frob ticket doable` every pass -- do not cache it across
  iterations, since state changes each pass.
