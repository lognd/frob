---
id: T-1612
title: 'Remove vestigial repo artifacts: FROBLEMS.md, skills/, agents/, keeping only
  frob-central tooling'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: high
parent: T-1609
tier: ticket
sprint: null
scope:
- FROBLEMS.md
- skills/**
- agents/**
- docs/**
- tests/unit/test_repo_hygiene.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_repo_hygiene.py
  reason: 'the deletion needs a lock: without a test, git add -f silently restores
    the tracked stale artifact'
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_clean.py::test_clean_deep_removes_frob_state
- tests/unit/test_repo_hygiene.py::TestUntrackedArtifacts::test_froblems_md_is_not_tracked
designated_repro_test: null
threat: null
component: null
---
Remove repository artifacts that are not central to frob's tooling, so what remains is all load-bearing.

Known candidates, named by the user: FROBLEMS.md and much of skills/ and agents/, which are vestigial. docs/guides/agent-playbook.md is explicitly worth KEEPING (it is the canonical home for process lessons this repo has already paid for once).

Rule to apply: anything not central to frob tooling goes. Anything that IS central stays, however scruffy.

Method, in this order, because deletion is the irreversible part:
1. Enumerate candidates and, for each, find every inbound reference (code, docs, config, CI, scaffolding templates, tests). frob's own refs machinery is the right instrument.
2. For each candidate, state plainly whether it is dead, partially live, or live-but-misplaced. A partially live artifact gets its live part extracted before the rest goes.
3. Delete, with each deletion attributable to this ticket in one commit per coherent group -- not one giant sweep, so any single removal can be reverted independently.
4. Re-run the full gate set afterwards. A deletion that silently reduces coverage or orphans a doc edge is the failure mode; the obligation graph should catch it, and if it does not, that is itself a finding worth a ticket.

Do not delete anything an in-flight ticket references. That is the whole reason this is gated behind the rest of the queue.