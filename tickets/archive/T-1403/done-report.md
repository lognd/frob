## Done report

Root cause isolated. The mechanism that let T-1390's uncommitted _land.py
and test changes land on main under c2fd45da's unrelated "file T-1402"
message is a two-part interaction:

1. A conflicted `git stash pop` auto-stages every file that merges
   cleanly. The mishap (popping a different worktree's T-0190 stash onto
   the shared main checkout) staged T-1390's wip alongside the conflicted
   files; `git reset --merge HEAD` backed out the conflicts but the
   cleanly-merged staged content survived in the index.

2. The ledger auto-commit helper `_add_and_commit_tickets_md`
   (src/frob/tickets/_leases.py:728, used by `frob ticket new`, `start`,
   `drop`, `fail` via commit_ticket_ledger_change/commit_start_transition)
   runs `git add tickets.md` then a BARE `git commit -m <message>`, which
   commits the entire index, not just tickets.md. The pre-staged wip rode
   into the next ticket-filing commit. Forensics confirm the shape:
   c2fd45da~1 is the genuine T-1402 filing (tickets.md only, +68), while
   c2fd45da carries only _land.py/test (+96/-10, +34) and does NOT touch
   tickets.md at all -- exactly what a swept index looks like.

Deliverables:
- Mechanical fix filed as T-1432 (pathspec-limit the ledger commit so it
  cannot carry passengers; regression test that a staged sentinel stays
  out of the commit and remains staged).
- Playbook lesson added: docs/guides/agent-playbook.md section 1b2
  (index-hygiene check after any stash mishap; never leave staged content
  on the shared checkout while frob verbs auto-commit).

No history rewrite performed: c2fd45da is already load-bearing on main
and the content is legitimate reviewed T-1390 work; the misleading
message is documented here and in section 1b2 rather than amended
(never amend a pushed commit).

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 1 error(s), 337 warning(s), 694 waived
- error-findings: PRE001@tickets/T-1403
