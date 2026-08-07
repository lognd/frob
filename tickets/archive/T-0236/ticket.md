---
id: T-0236
title: PRE001 stale-sweep churn in the multi-agent loop -- land should refresh the
  sweep
state: done
kind: ux
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestPreworkSweepRefresh::test_land_refreshes_stale_sweep_after_unrelated_main_change
- tests/test_ticket_land.py::TestPreworkSweepRefresh::test_sweep_refresh_failure_does_not_block_landing
designated_repro_test: null
threat: null
component: null
---
Three consecutive reviews (T-0181, T-0203, T-0202) REJECTed solely or partly on a stale PRE001 pre-work sweep, caused not by implementer negligence but by main moving between implementation and review in a multi-agent loop -- any unrelated landing that touches a ticket's scope globs invalidates its recorded sweep. Fix: frob ticket land refreshes the sweep against the post-merge state automatically before close (it already validates evidence/done-report pre-merge; add sweep-refresh as a post-merge, pre-close step), and frob check --ticket's PRE001 message should say when the staleness is due to out-of-scope-agent drift (compare sweep tree hash provenance) vs a genuinely un-swept scope change. Tests: land a ticket whose sweep predates an unrelated main landing; assert land succeeds and the recorded sweep is fresh.