---
id: T-0890
title: 'mutate: leftover mutant journal not auto-restored on next run start (xdist
  worker crash / external SIGTERM, beyond T-0857''s own-crash detection)'
state: dropped
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/mutate/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while working T-0855: `tests/test_tickets_mutation_evidence.py::
TestCheckTicketMutationEvidence::test_self_check_t0755_own_diff_zero_error_findings`
is a dogfooding self-check that runs `check_ticket_mutation_evidence`
against THIS repo's own real worktree root (mutating
src/frob/tickets/_mutation_evidence.py and src/frob/tickets/_land.py in
place, journaling originals via `frob.mutate._journal` for a safe revert
per T-0857).

Under heavy concurrent load on the machine (many other agent worktrees
running `frob check`/pytest simultaneously, observed directly via `ps
aux` while working T-0855), this test's pytest-xdist worker was observed
crashing outright ("[gw0] node down: Not properly terminated") while a
mutant was live, and separately, an EXTERNAL SIGTERM (a `timeout N`
wrapper killing the foreground pytest process from outside, not a crash
frob's own harness could detect) also left a mutant applied on disk --
both left `src/frob/tickets/_mutation_evidence.py` corrupted (formatting
collapsed, a boolean literal flipped) in the real worktree tree, with no
automatic recovery on the next run. T-0857 covers the case where
`frob.mutate`'s OWN harness detects its own crash and restores from the
journal; neither an xdist worker crash nor an external process kill goes
through that path, so the journaled backup in `.frob/mutate-backup/`
sits unused and the corrupted file is never auto-restored.

Both incidents were recovered manually here (`git show HEAD:<path>` to
get the clean committed original, since the corruption was on an
uncommitted working-tree file). Suggested fix direction: on `frob check`/
`frob test`/`pytest` startup (or via a dedicated `frob mutate restore`
subcommand run by CI/agent tooling at session start), scan
`.frob/mutate-backup/*.json` for journal entries whose target file's
current on-disk content does NOT match either the journaled original OR
a known-applied-mutant state expected by an in-progress run, and restore
from the journal automatically -- generalizing T-0857's crash-detection
restore to cover ANY leftover journal entry found stale at the start of
a fresh run, regardless of what killed the previous one.

## Drop reason
- 2026-07-26: exact duplicate of T-0885 (same body, same scope)