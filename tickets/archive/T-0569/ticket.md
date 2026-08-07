---
id: T-0569
title: 'ratchet pools: baseline semantics for new gate rules (error-for-new, tracked-baseline-for-old)'
state: done
kind: feature
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/pool_runner.py
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/__main__.py
- tests/test_gates_ratchet.py
- tests/test_pool_runner.py
- src/frob/gates/**
- frob.toml
- docs/modules/gates.md
- CHANGELOG.md
- docs/commands/cli-vocabulary.md
- docs/modules/tickets.md
- pyproject.toml
- src/frob/tickets/__init__.py
- src/frob/tickets/_brief.py
- src/frob/tickets/_models.py
- tests/test_tickets.py
- tests/test_tickets_brief.py
- tests/unit/test_main_entry.py
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/pool_runner.py
  reason: CLI wiring for frob pool snapshot/clear needed to make the ratchet mechanism
    usable, not just a library
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/app/app.py
  reason: CLI wiring for frob pool snapshot/clear needed to make the ratchet mechanism
    usable, not just a library
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/app/config.py
  reason: CLI wiring for frob pool snapshot/clear needed to make the ratchet mechanism
    usable, not just a library
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/__main__.py
  reason: CLI wiring for frob pool snapshot/clear needed to make the ratchet mechanism
    usable, not just a library
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_gates_ratchet.py
  reason: CLI wiring for frob pool snapshot/clear needed to make the ratchet mechanism
    usable, not just a library
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_pool_runner.py
  reason: CLI wiring for frob pool snapshot/clear needed to make the ratchet mechanism
    usable, not just a library
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/gates/**
  reason: 'structured scope from the ticket''s own prose Scope: line, prerequisite
    for TICK gates'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: frob.toml
  reason: 'structured scope from the ticket''s own prose Scope: line, prerequisite
    for TICK gates'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/modules/gates.md
  reason: 'structured scope from the ticket''s own prose Scope: line, prerequisite
    for TICK gates'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: CHANGELOG.md
  reason: 'SCOPE001 false-positive: T-0108''s commit-subject exemption needs the covering
    commit to name the ticket id; two earlier same-worktree commits (T-0578/T-0579)
    omitted it from the subject line, so their already-landed, already-evidenced files
    re-surface here instead of being exempt. Widening scope rather than rewriting
    shared worktree history.'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/commands/cli-vocabulary.md
  reason: 'SCOPE001 false-positive: T-0108''s commit-subject exemption needs the covering
    commit to name the ticket id; two earlier same-worktree commits (T-0578/T-0579)
    omitted it from the subject line, so their already-landed, already-evidenced files
    re-surface here instead of being exempt. Widening scope rather than rewriting
    shared worktree history.'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/modules/tickets.md
  reason: 'SCOPE001 false-positive: T-0108''s commit-subject exemption needs the covering
    commit to name the ticket id; two earlier same-worktree commits (T-0578/T-0579)
    omitted it from the subject line, so their already-landed, already-evidenced files
    re-surface here instead of being exempt. Widening scope rather than rewriting
    shared worktree history.'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: pyproject.toml
  reason: 'SCOPE001 false-positive: T-0108''s commit-subject exemption needs the covering
    commit to name the ticket id; two earlier same-worktree commits (T-0578/T-0579)
    omitted it from the subject line, so their already-landed, already-evidenced files
    re-surface here instead of being exempt. Widening scope rather than rewriting
    shared worktree history.'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'SCOPE001 false-positive: T-0108''s commit-subject exemption needs the covering
    commit to name the ticket id; two earlier same-worktree commits (T-0578/T-0579)
    omitted it from the subject line, so their already-landed, already-evidenced files
    re-surface here instead of being exempt. Widening scope rather than rewriting
    shared worktree history.'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/tickets/_brief.py
  reason: 'SCOPE001 false-positive: T-0108''s commit-subject exemption needs the covering
    commit to name the ticket id; two earlier same-worktree commits (T-0578/T-0579)
    omitted it from the subject line, so their already-landed, already-evidenced files
    re-surface here instead of being exempt. Widening scope rather than rewriting
    shared worktree history.'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'SCOPE001 false-positive: T-0108''s commit-subject exemption needs the covering
    commit to name the ticket id; two earlier same-worktree commits (T-0578/T-0579)
    omitted it from the subject line, so their already-landed, already-evidenced files
    re-surface here instead of being exempt. Widening scope rather than rewriting
    shared worktree history.'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_tickets.py
  reason: 'SCOPE001 false-positive: T-0108''s commit-subject exemption needs the covering
    commit to name the ticket id; two earlier same-worktree commits (T-0578/T-0579)
    omitted it from the subject line, so their already-landed, already-evidenced files
    re-surface here instead of being exempt. Widening scope rather than rewriting
    shared worktree history.'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_tickets_brief.py
  reason: 'SCOPE001 false-positive: T-0108''s commit-subject exemption needs the covering
    commit to name the ticket id; two earlier same-worktree commits (T-0578/T-0579)
    omitted it from the subject line, so their already-landed, already-evidenced files
    re-surface here instead of being exempt. Widening scope rather than rewriting
    shared worktree history.'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: 'SCOPE001 false-positive: T-0108''s commit-subject exemption needs the covering
    commit to name the ticket id; two earlier same-worktree commits (T-0578/T-0579)
    omitted it from the subject line, so their already-landed, already-evidenced files
    re-surface here instead of being exempt. Widening scope rather than rewriting
    shared worktree history.'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: 'SCOPE001 false-positive: T-0108''s commit-subject exemption needs the covering
    commit to name the ticket id; two earlier same-worktree commits (T-0578/T-0579)
    omitted it from the subject line, so their already-landed, already-evidenced files
    re-surface here instead of being exempt. Widening scope rather than rewriting
    shared worktree history.'
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_gates_ratchet.py::TestSnapshotRatchet::test_first_snapshot_baselines_every_key
- tests/test_gates_ratchet.py::TestSnapshotRatchet::test_second_snapshot_preserves_original_baseline_date
- tests/test_gates_ratchet.py::TestSnapshotRatchet::test_writes_committed_lock_file
- tests/test_gates_ratchet.py::TestSnapshotRatchet::test_two_rules_do_not_clobber_each_other
- tests/test_gates_ratchet.py::TestResolveRatchetSeverity::test_baselined_finding_stays_warn
- tests/test_gates_ratchet.py::TestResolveRatchetSeverity::test_fresh_finding_errors
- tests/test_gates_ratchet.py::TestResolveRatchetSeverity::test_unratcheted_rule_with_no_pool_is_error
- tests/test_gates_ratchet.py::TestClearRatchetEntry::test_clearing_requires_a_reason
- tests/test_gates_ratchet.py::TestClearRatchetEntry::test_clearing_with_reason_removes_entry_and_it_now_errors
- tests/test_gates_ratchet.py::TestClearRatchetEntry::test_clearing_unknown_key_is_err
- tests/test_gates_ratchet.py::TestRatchetEnabledRules::test_missing_toml_is_empty
- tests/test_gates_ratchet.py::TestRatchetEnabledRules::test_reads_configured_rules
- tests/test_gates_ratchet.py::TestRatchetEnabledRules::test_missing_table_is_empty
- tests/test_pool_runner.py::TestPoolSnapshotCli::test_snapshot_baselines_keys
- tests/test_pool_runner.py::TestPoolSnapshotCli::test_snapshot_requires_rule_and_keys
- tests/test_pool_runner.py::TestPoolClearCli::test_clear_removes_entry_with_reason
- tests/test_pool_runner.py::TestPoolClearCli::test_clear_requires_reason
- tests/test_pool_runner.py::TestPoolRunDispatch::test_unknown_command_exits_nonzero
designated_repro_test: null
threat: null
component: null
---
Every warn-first detector this session (INV 765, COV ~160, PII 336, DEAD 51) needed a hand-managed calibrate+burndown campaign. frob pool snapshot RULE freezes existing findings as a tracked baseline (each entry needs eventual disposition, TICK004-style rot applies); NEW findings error immediately. Replaces warn-pool campaigns with a self-draining ratchet. Scope: src/frob/gates/, frob.toml schema, docs/modules/gates.md.