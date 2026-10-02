---
id: T-0036
title: 'frob-ledger: first-class evidence, evidence-bypass and land events with an
  append API'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: medium
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 3
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
- crates/frob-evidence/src/**
- crates/frob-land/src/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given an evidence event with accepts, when the ticket is folded, then the
    matching acceptance items are bound
  evidence: []
- text: Given frob-evidence and frob-land, when grepped for commit_paths, then neither
    calls it directly
  evidence: []
threat: null
component: frob-ledger
anchor: false
anchor_reason: null
land_commit: null
---
frob-evidence and frob-land each copy a private commit helper to write event files and re-fold ticket.md because EventBody has no Evidence, EvidenceBypass or Land variants and commit_events is pub(crate). Add the variants (fold binds acceptance[].bound from evidence accepts; land records base ref, commit oid, pushed), a public Ledger::append(ticket, EventBody) that writes, re-folds and commits on the ledger ref, and switch frob-evidence and frob-land to it, deleting the copies.