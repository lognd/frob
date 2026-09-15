---
id: T-draft-725f3c4c
title: 'Lease staleness probe re-parses the whole ticket archive (3391 YAML files)
  once per lease record: read_all_leases costs minutes and lands sit silent CPU-bound'
state: queued
kind: bug
origin: agent
created: '2026-09-15'
priority: critical
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/_archive.py
- tests/unit/test_leases_staleness_perf.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN N live lease records WHEN _live_leases_pruning_stale runs THEN the ticket
    ledger is loaded at most once per call (counted via a monkeypatched load_queue),
    not once per record
  evidence: []
- text: GIVEN a ticket id present under tickets/archive WHEN the staleness shape is
    computed THEN it answers ticket-terminal without YAML-parsing the archive
  evidence: []
- text: GIVEN this repo (899 active, 3391 archived tickets) WHEN read_all_leases is
    timed with the current worktree set THEN it completes in under 5 seconds (record
    before and after in the Done report)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-15 with two SIGUSR1 stack dumps 60 s apart on a live land of T-draft-926571db (pid 75356, 100 percent CPU, no log line for 10+ min): both dumps sit in yaml.load <- _store._parse_ticket_file <- _store.load_archive <- _archive._load_merged <- _archive.load_queue <- _leases._ticket_ledger_staleness_shape (line 972) <- _live_leases_pruning_stale (line 4119) <- read_all_leases (3890) <- _land._effective_leakage_scope <- _find_leaked_tickets <- _check_cross_ticket_leakage <- _land_precheck. _ticket_ledger_staleness_shape calls load_queue(root) per lease record; load_queue merges the archive, YAML-parsing all 3391 archived tickets every time. With ~20 registered worktrees that is ~70k file parses per read_all_leases, and the land calls read_all_leases more than once. This is the unfiled 'land CPU-bound 25+ min after the wip commit with no child process' bug from 2026-09-12 and the reason a first land on a fresh branch takes 20+ minutes. Fix: load the queue once per pruning pass and pass it down; answer archive membership by tickets/archive/<id> existence; consider a per-process ledger cache keyed by directory mtime. Do not change lease semantics.