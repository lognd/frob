---
id: T-1403
title: 'Investigate: T-1390 worktree changes landed on main under an unrelated commit
  message (c2fd45da)'
state: done
kind: docs
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:bash -c "grep -q '^## 1b2' docs/guides/agent-playbook.md && grep -q 'T-1432'
  docs/guides/agent-playbook.md && git show c2fd45da --stat | grep -q _land.py" exit=0
  sha256=e3b0c44298fc
designated_repro_test: null
threat: null
component: null
---
While landing T-1390, a `git stash pop` (accidentally run against agent-playbook.md
section 1b's advice, while diagnosing an unrelated pre-existing test flake) popped
a DIFFERENT worktree's stash entry ("On worktree-agent-aba2276bbee55aece: T-0190
wip") onto this shared main checkout, producing a merge conflict in
tests/test_secrets_gate.py and a staged tickets.md change. The conflicted pop was
reverted cleanly with `git reset --merge HEAD` (the stash entry itself was never
dropped, since a conflicted pop leaves it in the stash list -- confirmed with
`git stash list` before and after).

Separately (root cause not yet isolated), T-1390's own in-progress, pre-refactor
_land.py/test changes ended up committed onto main under commit c2fd45da, whose
message is "chore(tickets): file T-1402 gate-precision epic for the v1.0.0
zero-warning bar" -- an unrelated ticket-filing commit that should only have
touched tickets.md. The commit's actual diff (+96/-10 in src/frob/tickets/_land.py,
+34 in tests/unit/test_land_cross_ticket_leakage.py) is legitimate, reviewed T-1390
work (the same code this ticket's own Done report cites), just mislabeled and
landed a commit earlier/differently than intended. A follow-up commit
(7a402998, "fix(tickets): split _find_leaked_tickets under ARCH001's line
threshold") on top corrects the ARCH001 violation the premature commit still had.

Filing this because: (1) main's commit history now has a misleading message next
to real code, which could confuse `git blame`/bisect later, and (2) the underlying
mechanism that let uncommitted worktree changes land under an unrelated commit
message during a stash mishap is not understood and should be investigated before
another agent hits it. No code was lost; both commits are on main and gates clean.