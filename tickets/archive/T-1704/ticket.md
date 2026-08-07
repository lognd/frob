---
id: T-1704
title: 'Ledger-mutating ticket verbs auto-commit inconsistently: block/scope/priority
  leave root dirty and DirtyMain-block every agent'
state: dropped
kind: bug
origin: agent
created: '2026-08-06'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/app/ticket_runner/_new.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
`frob ticket new`/`drop`/`fail`/`done-report`/`evidence` auto-commit
their ledger write (T-1130/T-1178, each with a `--no-commit` opt-out).
`frob ticket block`, `scope`, `priority`, `kind`, `component`, `label`,
`accept`, `attach`, `tier`, `sprint` and friends mutate the same
`tickets.md` and DO NOT.

That inconsistency is a live hazard, not a cosmetic wart. Observed twice
in one session on 2026-08-06: a coordinator ran `frob ticket block` twice
against the root checkout to add two dependency edges, and the
uncommitted `tickets.md` residue -- a two-blank-line normalisation, no
semantic change at all -- refused every subsequent `frob ticket land`
from every worktree-isolated agent with `DirtyMain`. One agent burned
five retries and its remaining budget before stopping. It could not fix
it: an agent is correctly forbidden from committing state it does not
own, and cannot even inspect root.

The failure is silent and asymmetric: the verbs a person reaches for most
often while triaging a queue (block, scope, priority) are exactly the
ones that leave the repo in a state that blocks everyone else, while the
verbs that create work commit cleanly. Nothing in the output warns about
it.

Fix: make ledger-mutating verbs auto-commit UNIFORMLY, via one shared
helper rather than per-verb repetition -- the existing T-1130/T-1178
implementations should be the thing extracted, not copied. Every such
verb honours the same `--no-commit` opt-out for callers that batch
several edits before committing.

Requirements:

- Enumerate the verbs from the dispatch table rather than by hand, so a
  verb added later cannot silently miss the behaviour. A hand-written
  list is the same class of defect as this ticket.
- A verb that writes nothing (a no-op edit) must not create an empty
  commit.
- Commit message names the verb and the ticket, e.g.
  `chore(tickets): block T-1688 by T-1703`.
- `--no-commit` must WARN that it is leaving the ledger dirty and that
  this will block concurrent lands, naming the fix. A silent opt-out
  reproduces the incident with an extra step.

Regression coverage: for every ledger-mutating verb in the dispatch
table, invoking it leaves the repo CLEAN. Assert it over the enumerated
table, not over a hand-picked sample, so the test fails when someone adds
verb number twelve.

Related: T-1699 (DirtyMain misreads coordinator-owned dirt as a crashed
land) is the diagnosis half of the same incident class; this ticket is
the prevention half.

## Drop reason
- 2026-08-06: duplicate of T-1615, filed 2026-08-05 from the same incident (two frob ticket block edges leaving tickets.md dirty, next land refused with DirtyMain). T-1615 is the stronger spec: it requires an audit table across every ledger-writing verb as the deliverable, not just the block fix, plus a parameterized test over the verb list. Filed T-1704 without grepping the queue first -- the exact check I had just instructed the agents to perform (absorbed by T-1615)