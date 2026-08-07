## Done report

Fixed the wave-17 dominant fallout class: renumber_one (and its two
callers, finalize_draft / frob ticket land, and the bare `frob ticket
renumber OLD NEW` CLI) rewrote only structural ledger fields (a ticket's
own id, blocked_by, parent) plus code directive lines -- never free-text
Done-report/description PROSE citing a renumbered id elsewhere in
tickets.md/tickets-archive.md. A sibling ticket's "Filed: T-draft-xxxx"
or a description naming another ticket went permanently stale the moment
that id was renumbered: either a TICK006 phantom once a dead draft id no
longer resolved, or (worse, invisible to any gate) a citation of the WRONG
real id if a hand-guessed final id happened to already be taken by
something else (the T-0668 8-site incident cited in the ticket body).

Added `_rewrite_body_prose_references` (whole-word regex substitution,
scoped to the renumber mapping's actual old->new pairs) and wired it into
`_apply_renumber` (used by both `renumber()`'s bulk contiguous remap and
`renumber_one`'s single-id remap via `_apply_renumber_mapping`), so every
ticket's body prose is rewritten in the SAME ledger_lock transaction as
the structural id fields -- for both the active and archive stores.
`_apply_renumber`'s "touched" count now includes a ticket whose body was
rewritten even if its own id did not change, so `_persist_renumber`'s
write-trigger actually persists it. `RenumberReport.occurrences` now
folds prose-hit counts in alongside code-reference hits.

This closes both of T-1125's acceptance criteria: a draft id finalized at
land time (finalize_draft -> renumber_one) rewrites a sibling ticket's
prose citation of it, and the standalone `frob ticket renumber OLD NEW`
CLI path does the same.

Updated docs/modules/tickets.md's public-api section for `renumber`/
`renumber_one` to document the new prose-rewrite behavior (closes the
AFFECT001 doc-drift finding this diff otherwise triggers).

Out of scope, not touched: the pre-existing SCOPE002 scope-closure debt
across T-1125's broad `src/frob/tickets/**` scope glob (~548 warnings,
one promoted to error until scope was extended to cover the two files
this ticket's own diff actually touches -- docs/modules/tickets.md and
tests/test_tickets_collision.py; both added via `frob ticket scope
--add`). That debt is unrelated to this diff and pre-exists across the
whole ticket family (see TICK009's "chronically over-broad glob" findings
for many other tickets in this same package) -- filed as a follow-up
draft ticket rather than chased down here.

Filed: T-1145 (scope-closure debt across src/frob/tickets/**
ticket-scope globs; a draft id, renumbers at land -- cite the real id
once landed).

### Changed
```
 docs/modules/tickets.md           |  14 +++++
 src/frob/tickets/_new_renumber.py | 122 +++++++++++++++++++++++++++++++-------
 tests/test_tickets_collision.py   |  99 +++++++++++++++++++++++++++++++
 tickets.md                        |  75 ++++++++++++++++++++++-
 4 files changed, 288 insertions(+), 22 deletions(-)
```

### Evidence
- `tests/test_tickets_collision.py::TestRenumberRewritesLedgerProse::test_renumber_one_rewrites_a_sibling_ticket_done_report_prose` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberRewritesLedgerProse::test_finalize_draft_rewrites_a_sibling_ticket_done_report_prose` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 15 error(s), 944 warning(s), 424 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:295, INV006@src/frob/app/ticket_runner/_mutate.py, SELFAUDIT001@design, TICK006@tickets.md
