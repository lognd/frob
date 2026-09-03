---
id: T-3536
title: 'macOS: natives-build test asserts on cargo progress chatter; assert the outcome
  instead'
state: done
kind: bug
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_natives_build_integration.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record macOS-only BUG002 waiver per series instructions
  actor: logan
  at: '2026-08-31'
  old_length: 0
  new_length: 458
- mode: append
  reason: record macOS-only BUG002 waiver per series instructions
  actor: logan
  at: '2026-08-31'
  old_length: 458
  new_length: 918
- mode: append
  reason: record macOS-only BUG002 waiver
  actor: logan
  at: '2026-08-31'
  old_length: 918
  new_length: 1244
evidence:
- tests/system/test_natives_build_integration.py::test_build_natives_compiles_and_imports_real_crate
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 4dfb69e1b721ee95c301dfdc156c923ee1fa16dc
---
frob:waive BUG002 reason="macOS-only defect, ground-truth verified from CI run 33353658750 job 99371615032 (AssertionError showing only cargo Updating crates.io index / Locking N packages chatter as the stderr diagnostic); real cause is pytest-timeout(180) killing the maturin/cargo subprocess mid crates.io-index-clone on a slow/cold macOS runner network, not a reproducible compile bug, so it cannot fail-then-pass on this Linux dev box with a warm cache."

frob:waive BUG002 reason="macOS-only defect, ground-truth verified from CI run 33353658750 job 99371615032 (AssertionError showing only cargo Updating crates.io index / Locking N packages chatter as the stderr diagnostic); real cause is pytest-timeout(180) killing the maturin/cargo subprocess mid crates.io-index-clone on a slow/cold macOS runner network, not a reproducible compile bug, so it cannot fail-then-pass on this Linux dev box with a warm cache."

frob:waive BUG002 reason="macOS-only defect verified from CI run 33353658750 job 99371615032; real cause is pytest-timeout(180) killing the maturin/cargo subprocess mid crates.io-index-clone on a slow macOS runner network, not a reproducible compile bug, so it cannot fail-then-pass on this Linux dev box with a warm cache."