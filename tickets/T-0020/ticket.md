---
id: T-0020
title: 'frob-evidence + frob-tests: evidence providers, dir store, touched-set test
  selection'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0018
- T-0009
- T-0013
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 8
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
- crates/frob-evidence/**
- crates/frob-tests/**
- crates/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a worktree where one function changed, when frob test --base main runs,
    then only tests reaching that function run and an evidence event is appended
  evidence: []
- text: Given a ticket of a code-changing type with no measured evidence, when close
    runs, then exit is 3 with the remedy naming frob test
  evidence: []
threat: null
component: frob-evidence
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/frob-evidence and crates/frob-tests per tickets.md section 9 (dir: and https stores only for M1 per audit M35) and build-test-ci.md. Evidence record = event kind evidence { provider, ref, digest, uri, status measured|unmeasured, captured_at }; providers: nextest (parse libtest JSON or junit from cargo nextest via gob-exec with the Cargo program class), command (arbitrary allowlisted tool output with redaction), file (hash a path). Blobs under 16 KiB (knob) inline, larger ones in the dir: store (default .git/frob/artifacts, non-authoritative) addressed by blake3. ticket evidence add|list|fetch verbs; the close guard trait from frob-ledger is implemented here: close requires at least one measured evidence record for code-changing types unless --no-evidence --reason. frob-tests: touched set = files changed against --base mapped through gob-symbols affects() to Rust test functions and their packages; frob test --base <ref> runs cargo nextest with the selected filter via gob-exec, records evidence on the active ticket when run in a worktree. TEST001 rule: frob:tests directive names a test that does not exist.