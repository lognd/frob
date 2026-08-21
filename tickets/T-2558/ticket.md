---
id: T-2558
title: T-2556's ticket body cites frob scaffold install-worktree-lease-hook, which
  does not exist -- DOC006 land-blocker
state: dropped
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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

## Failure log
- 2026-08-20 attempt 1: Premise already resolved: T-2556 landed as done (commit 5b1cbab1ac9d1c58571dc69dc6a163e3f2613ad8) and its current ticket.md body no longer contains the string 'install-worktree-lease-hook' anywhere (git grep confirms zero hits in tickets/T-2556/ticket.md; the phrase survives only in T-2556's own done-report.md prose and unrelated T-2071, neither of which DOC006 flagged). Directly ran tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo: it still fails, but on exactly one unrelated DOC006 finding (docs/audits/test005-zero-classification-t1418.md:9, a broken heading anchor into docs/guides/agent-playbook.md) -- no finding traces to T-2556 at all. Also independently confirmed the cited scaffold subcommand genuinely does not exist (frob scaffold --help lists list/apply/new/pool only), matching this ticket's own claim, but that claim is now moot since the citation is already gone. Nothing to fix under this ticket's scope (tickets/T-2556); requeuing rather than forcing scope. The one remaining live DOC006 finding is a separate, unrelated defect outside this ticket's scope.

## Drop reason
- 2026-08-21: already resolved: T-2565 (landed 2026-08-18) retired the citation, confirmed via git log -S install-worktree-lease-hook as a command that never existed rather than a rename; T-2556 body no longer contains the string (2026-08-21) (absorbed by T-2565)
