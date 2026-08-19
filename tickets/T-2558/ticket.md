---
id: T-2558
title: T-2556's ticket body cites frob scaffold install-worktree-lease-hook, which
  does not exist -- DOC006 land-blocker
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tickets/T-2556
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: avoid backtick-wrapped bogus/gap CLI invocations tripping DOC006 on the
    ticket's own body (land-blocking as of T-2374)
  actor: logan
  at: '2026-08-18'
  old_length: 1420
  new_length: 1475
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2533 (DOC006 CLI-invocation false-positive fix):
tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::
test_doc004_doc006_zero_against_live_repo fails against current main with
a DOC006 finding unrelated to T-2533's own fix:

tickets/T-2556/ticket.md line 29 cites a scaffold subcommand named
install-worktree-lease-hook (frob scaffold, no backticks -- see the
ticket text for the exact wording), which does not resolve to a known
subcommand. Confirmed directly by walking frob.__main__._build_parser()'s
real tree: scaffold's real subcommands are apply/list/new/pool (pool's
own subcommands: lease/status/warm) -- no install-worktree-lease-hook
anywhere. This is NOT a gate false positive (unlike T-2533's
bypassed-verb class) -- the cited command genuinely does not exist under
any name.

T-2556 is still open (queued/in-progress), so DOC006's historical-ticket
exemption (_is_historical_ticket_doc, only applies to DONE/DROPPED
tickets) correctly does not suppress this -- it will keep failing DOC006
(now land-blocking per T-2374) until either the command is implemented as
T-2556 describes, or its ticket body is corrected to name the real
mechanism.

Fix: read T-2556's actual intent (a pre-commit hook installer for the
worktree-lease guard) and either (a) implement the missing scaffold
subcommand if that is genuinely the intended UX, or (b) correct T-2556's
own body text to describe however that hook actually gets installed
today.
