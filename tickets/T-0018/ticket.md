---
id: T-0018
title: 'frob-ledger: ULID tickets, events, fold, index, merge driver, core ticket
  verbs'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0010
- T-0017
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 13
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- crates/frob-ledger/**
- crates/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: crates/gob-macros/**
  reason: TicketField derive split into a follow-up so the ledger and directives tickets
    can run in parallel
  actor: logan
  at: '2026-10-02'
designated_repro_test: null
acceptance:
- text: Given a temp repo, when ticket new then update then close run, then events
    exist for each, the frontmatter equals the fold, and three commits exist on the
    ledger ref with only tickets/ paths
  evidence: []
- text: Given two branches each adding events to the same ticket, when merged with
    the merge driver, then all events survive and the frontmatter is re-folded
  evidence: []
- text: Given a ticket handle that matches two tickets, when show runs, then exit
    is 3 with both candidates
  evidence: []
threat: null
component: frob-ledger
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/frob-ledger per tickets.md sections 2 to 5 and 11 as updated by D23, D24, D33, D34, and exceptions for M1 (accept and defer only). Storage: tickets/<ulid>/ticket.md with TOML frontmatter (schema via #[derive(TicketField)] in gob-macros generating serde, schema and the docs table) and events/<ulid>.toml append-only; frontmatter is the fold of events and integrity = equals-fold. Ticket types per tickets.md (minus milestone), categories triage|todo|in-progress|blocked(derived)|done plus outcome, structured story fields optional in M1, typed links from the canonical link table with inverses. Writes go through gob-git commit_paths on the ledger ref ([tickets] ref knob, default trunk; branch mode). Index: SQLite table in gob-cache keyed by the ledger tree id, rebuilt on mismatch, used by list and show (< 50 ms warm). Verbs (via gob-cli Command derive, in the frob binary): ticket new (with --idempotency-key, structured flags, --scope, --points, --parent, --blocked-by, --acceptance), show, list (filters by state, type, parent, label), update (patch), link/unlink, comment, close (guards: outcome required, evidence hook left as a trait for frob-evidence), drop --reason, reopen --reason, doable (no open blockers, lease-safe hook as a trait), brief, doctor (ledger integrity), merge-driver (hidden; union events then re-fold). Handles: full ULID canonical; unique suffix handle accepted on input. TICK rules: TICK001 frontmatter differs from fold, TICK002 referenced ticket not on base, TICK003 dangling link. Trial error_set for this crate's error types per D22 and report on it in the done-report. Dogfood: this ticket's tests create a temp repo and run the whole lifecycle.