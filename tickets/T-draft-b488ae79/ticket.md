---
id: T-draft-b488ae79
title: evidence --replace/--remove is not mirrored to the primary checkout, so frob
  ticket land refuses on stale evidence it already rebound away from
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/app/ticket_runner/_ledger_mirror.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: measured while landing T-4143 in this session
  actor: logan
  at: '2026-09-07'
  old_length: 1910
  new_length: 2480
- mode: append
  reason: confirmed via direct reproduction while landing T-4143 in this session
  actor: logan
  at: '2026-09-07'
  old_length: 2480
  new_length: 8775
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Description: `frob ticket land` refuses with "evidence no longer resolves
post-merge" against evidence ids that DO still resolve on the landing
branch, because `_reverify_evidence_post_merge` (src/frob/tickets/_land.py)
loads the ticket via `_load_one(worktree, ticket_id)` where `worktree` can
resolve stale state: the primary checkout's own mirrored copy of the
ticket (`chore(tickets): mirror scope T-#### from worktree` commits) is
kept current for SCOPE changes only -- `mirror_ledger_change_to_primary`
is invoked from the scope-mutation path but not from
`replace_evidence`/`remove_evidence`. A ticket that runs
`frob ticket evidence --replace OLD NEW` after an earlier scope mirror has
already run ends up with its evidence rebind invisible to the primary
checkout, so a subsequent `frob ticket land` on that ticket refuses citing
the OLD (already-rebound-away) node id, even though the actual landing
branch's own ticket.md has the correct, current evidence list.

Measured live: T-4143 (this session) hit this exactly -- `replace_evidence`
rebound two evidence ids to a new test file (to resolve an unrelated
CrossTicketLeakage against a sibling ticket), the ticket's own worktree
branch showed the correct evidence immediately, but `frob ticket land`
repeatedly refused with the OLD ids across three retries, and the primary
checkout's tickets/T-4143/ticket.md was confirmed (read-only) to still
list the pre-replace ids.

What to do: audit every ledger-mutating verb for whether it calls
`mirror_ledger_change_to_primary` (or should) -- `replace_evidence`/
`remove_evidence` at minimum need it, and this may be a broader gap
(other mutation verbs worth auditing too). Do NOT hand-fix by editing the
primary checkout's ticket file directly -- that is the exact anti-pattern
this repo's "coordinator never dirties root" rule exists to prevent; the
fix belongs in the mirroring call sites themselves.


Refined finding (measured across 3+ retries, no intervening changes): the worktree's OWN tickets/T-4143/ticket.md is confirmed correct (new evidence ids) at every retry, yet frob ticket land repeatedly refuses citing the OLD (already-rebound-away) ids as 'no longer resolves post-merge'. This suggests _load_one(worktree, ticket_id) inside _reverify_evidence_post_merge is not reading the current tip of the --worktree path at that point in _land_locked -- possibly a squash/compose stage reads a stale snapshot. Needs real instrumentation, not more black-box retries.

CONFIRMED ROOT CAUSE (not a squash/compose staleness bug as I guessed earlier): merging main into the ticket's own worktree branch (git merge main) pulls in the primary checkout's stale mirrored ticket.md (evidence never mirrors, only scope/state-adjacent verbs do) and git's plain line-based merge UNIONS the primary's old evidence entries alongside the branch's already-rebound ones instead of conflicting, since both look like independent list insertions to a 3-way diff. This duplicates evidence -- the OLD, no-longer-existing ids sit right next to the NEW, correct ones -- and land's post-merge resolution check then correctly refuses on the stale duplicates. Confirmed by direct inspection of the merged ticket.md (both old and new node ids present) and fixed by hand-removing the duplicated old lines (a real, git-recognized merge-conflict-shaped resolution, not a guess) before retrying land, which then succeeded. This will recur for ANY ticket that (a) runs a scope-mirrored verb, then (b) runs replace_evidence/remove_evidence, then (c) needs Merge made by the 'ort' strategy.
 CHANGELOG.md                                     |   6 +
 changelog.d/T-4143.md                            |   2 +
 changelog.d/T-4167.md                            |   2 +
 changelog.d/T-4170.md                            |   2 +
 changelog.d/T-4191.md                            |   2 +
 changelog.d/T-4243.md                            |   2 +
 changelog.d/T-4244.md                            |   2 +
 src/frob/app/ticket_runner/_rapid_sweep.py       |  20 +-
 src/frob/tickets/_evidence.py                    | 107 ++++++-
 src/frob/tickets/_land.py                        |  28 +-
 src/frob/tickets/_models.py                      |  57 +++-
 tests/system/test_cli_evidence_enforcement.py    |   6 +-
 tests/test_evidence_integrity.py                 | 219 ++++++++++++++
 tests/test_ticket_leases.py                      |  30 ++
 tests/test_tickets.py                            | 123 +++++++-
 tests/test_tickets_evidence_replace_cmd_t4143.py | 144 +++++++++
 tests/ticket_land_suite/test_land_core.py        |  11 +-
 tests/ticket_land_suite/test_wip.py              |  18 +-
 tests/unit/arch_suite/test_misc.py               |   9 +-
 tests/unit/rapid_sweep_suite/test_filing.py      |   4 +-
 tests/unit/test_flag_coverage_gate.py            |   6 +-
 tests/unit/test_lang_primitives.py               |   9 +-
 tickets/T-3936/ticket.md                         |  82 ++++-
 tickets/T-4143/done-report.md                    | 125 ++++++++
 tickets/T-4143/ticket.md                         |  32 +-
 tickets/T-4167/done-report.md                    | 116 +++++++
 tickets/T-4167/ticket.md                         |  32 +-
 tickets/T-4170/done-report.md                    |  89 ++++++
 tickets/T-4170/ticket.md                         |  27 +-
 tickets/T-4191/done-report.md                    |  55 ++++
 tickets/T-4191/ticket.md                         |  18 +-
 tickets/T-4243/done-report.md                    | 120 ++++++++
 tickets/T-4243/ticket.md                         |  19 +-
 tickets/T-4244/done-report.md                    | 100 ++++++
 tickets/T-4244/ticket.md                         |  39 ++-
 tickets/T-4246/ticket.md                         |  95 ++++++
 tickets/T-4247/ticket.md                         |  30 ++
 tickets/T-4248/ticket.md                         |  30 ++
 tickets/T-4249/ticket.md                         |  32 ++
 tickets/T-4250/ticket.md                         |  30 ++
 tickets/T-4252/ticket.md                         |  30 ++
 tickets/T-4253/ticket.md                         |  30 ++
 tickets/T-4254/ticket.md                         |  30 ++
 tickets/T-4255/ticket.md                         | 183 +++++++++++
 tickets/T-4257/ticket.md                         |  88 ++++++
 tickets/T-4258/ticket.md                         | 125 ++++++++
 tickets/T-4259/ticket.md                         | 107 +++++++
 tickets/T-4260/ticket.md                         |  80 +++++
 tickets/T-4261/ticket.md                         |  70 +++++
 tickets/T-4262/ticket.md                         |  48 +++
 tickets/T-4263/ticket.md                         |  82 +++++
 tickets/T-4264/ticket.md                         | 370 +++++++++++++++++++++++
 tickets/T-4265/ticket.md                         |  83 +++++
 53 files changed, 3138 insertions(+), 68 deletions(-)
 create mode 100644 changelog.d/T-4143.md
 create mode 100644 changelog.d/T-4167.md
 create mode 100644 changelog.d/T-4170.md
 create mode 100644 changelog.d/T-4191.md
 create mode 100644 changelog.d/T-4243.md
 create mode 100644 changelog.d/T-4244.md
 create mode 100644 tests/test_tickets_evidence_replace_cmd_t4143.py
 create mode 100644 tickets/T-4143/done-report.md
 create mode 100644 tickets/T-4167/done-report.md
 create mode 100644 tickets/T-4170/done-report.md
 create mode 100644 tickets/T-4191/done-report.md
 create mode 100644 tickets/T-4243/done-report.md
 create mode 100644 tickets/T-4244/done-report.md
 create mode 100644 tickets/T-4246/ticket.md
 create mode 100644 tickets/T-4247/ticket.md
 create mode 100644 tickets/T-4248/ticket.md
 create mode 100644 tickets/T-4249/ticket.md
 create mode 100644 tickets/T-4250/ticket.md
 create mode 100644 tickets/T-4252/ticket.md
 create mode 100644 tickets/T-4253/ticket.md
 create mode 100644 tickets/T-4254/ticket.md
 create mode 100644 tickets/T-4255/ticket.md
 create mode 100644 tickets/T-4257/ticket.md
 create mode 100644 tickets/T-4258/ticket.md
 create mode 100644 tickets/T-4259/ticket.md
 create mode 100644 tickets/T-4260/ticket.md
 create mode 100644 tickets/T-4261/ticket.md
 create mode 100644 tickets/T-4262/ticket.md
 create mode 100644 tickets/T-4263/ticket.md
 create mode 100644 tickets/T-4264/ticket.md
 create mode 100644 tickets/T-4265/ticket.md pulled into its worktree before landing (e.g. to pick up sibling tickets for a start-time scope-collision check, as happened here) -- the merge step is the trigger, not land itself. Fix options: mirror evidence changes too (matching this ticket's original title), or make the ledger merge driver conflict-aware for the evidence list specifically (e.g. a custom git merge driver for tickets/*/ticket.md), so a genuine divergence always conflicts instead of silently unioning.