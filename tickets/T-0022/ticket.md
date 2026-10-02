---
id: T-0022
title: 'frob-obligations: COV, TODO, DOC, REF, INV rule subset'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0021
- T-0018
- T-0015
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
- crates/frob-obligations/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given each rule's corpus, when the mdtests run, then every rule has a passing
    fire and clean case
  evidence: []
- text: Given a frob:defer bound to a ticket that is done, when check runs, then EXC003
    fires and the suppressed finding is shown
  evidence: []
threat: null
component: frob-obligations
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/frob-obligations per rules.md section 2 families table for the M1 subset: COV001 public symbol with no test reaching it (via gob-symbols reach and nextest test list), COV003 frob:tests names a missing test (shared with TEST001, pick one owner and record it), TODO001 bare TODO/FIXME without frob:todo <ulid>, TODO002 frob:todo pointing at a terminal ticket, DOC001 public symbol without rustdoc (tree-sitter, complements the compiler lint for non-Rust later), DOC002 markdown link to a missing file or anchor inside the repo, REF001 frob:ticket pointing at a missing ticket, INV001 invariant file under invariants/ with no frob:invariant binding, INV002 forbidden import per [invariants] rules (uses gob-symbols imports). Each rule has an mdtest corpus with fire and clean cases via gob-mdtest. Exceptions: accept and defer directives from gob-directives suppress with EXC001 (bad reason), EXC003 (defer ticket terminal), EXC005 (accept stale: body digest changed since attested), EXC007 (defer ticket missing) evaluated here against the ledger.