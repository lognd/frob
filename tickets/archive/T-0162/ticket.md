---
id: T-0162
title: make ticket-id collision structurally impossible across checkouts and worktrees
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- src/frob/app/**
- src/frob/__main__.py
- tests/**
- docs/modules/tickets.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_collision.py::TestPostArchiveReissueIncident::test_new_ticket_never_reissues_an_archived_id
- tests/test_tickets_collision.py::TestTwoCheckoutConcurrentFilingIncident::test_two_worktrees_file_concurrently_no_collision
- tests/test_tickets_collision.py::TestSweepWorktreeCollisionIncident::test_renumber_one_rewrites_ledger_and_many_code_references
- tests/test_tickets_collision.py::TestSweepWorktreeCollisionIncident::test_dry_run_reports_without_writing
- tests/test_tickets_collision.py::TestTick002GateUnwaivable::test_draft_id_on_default_branch_is_a_violation
- tests/test_tickets_collision.py::TestTick002GateUnwaivable::test_tick002_is_unwaivable
- tests/test_tickets_collision.py::TestTick002GateUnwaivable::test_no_violation_off_default_branch
designated_repro_test: null
threat: null
component: null
---
Third collision incident in one day: (1) post-archive allocator reissued T-0001 (fixed by T-0140, active+archive max); (2) T-0144 reserved in one worktree while main allocated the same id (avoided by manual coordination); (3) a sweep worktree filed T-0157 while main independently assigned T-0157 to a different ticket, with ~102 code waiver comments referencing the collided id (fixed by manual sed renumber). Root cause: sequential max+1 allocation in independent checkouts that later merge -- the allocator cannot see sibling worktrees or unmerged branches, and coordination is manual. REQUIRED INVARIANT: two ledgers filed independently in ANY two checkouts/branches/worktrees must never merge into the same final id, with no human coordination. Design the mechanism (implementer chooses with a written decision record in docs/modules/tickets.md; candidates to evaluate): (a) PROVISIONAL IDS -- frob ticket new off the default branch mints a draft id (e.g. T-draft-<8-char content/branch hash>), and a frob ticket finalize/land step (run at merge/land time, or automatically by a gate) assigns the next sequential T-#### and atomically rewrites the ledger section AND every code directive referencing the draft id; final ids only ever minted against the default branch's merged view, making collision structurally impossible; (b) branch-tip scanning as defense-in-depth -- allocation also scans tickets.md at every local ref tip so sibling worktrees' filings are visible; (c) content-nonce tiebreak. Whatever the choice: a new gate rule must fail frob check loudly on duplicate ids ANYWHERE (active+archive+draft) and on draft ids that survived onto the default branch; plus frob ticket renumber <old> <new> as a first-class command doing the atomic ledger+code-reference rewrite (no more sed), with a dry-run mode; plus tests reproducing all three real incidents above and proving the invariant (two simulated checkouts file concurrently, merge, no collision, references intact). Update ~/.claude/refs-worthy docs in docs/modules/tickets.md including the agent workflow implications (agents file freely in worktrees, finalize happens at land).