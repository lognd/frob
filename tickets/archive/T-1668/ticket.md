---
id: T-1668
title: Delete 37 obsolete frob:waive OPAQUE001 directives left stale by T-1659's semantic
  rewrite
state: done
kind: docs
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability_scan.py
- src/frob/deploy/_conform.py
- src/frob/dup/_pipeline/_smt.py
- tests/test_gates.py
- tests/test_graph_lock.py
- tests/test_ticket_land.py
- tests/test_gates_suppress.py
- tests/test_app.py
- tests/test_ticket_work_and_land_finish.py
- tests/test_tickets_collision.py
- tests/test_tickets_evidence_cli.py
- tests/unit/test_check_tool_unavailable.py
- tests/unit/strata/test_conform_eval_needle.py
- tests/unit/test_main_entry.py
- tests/test_dup.py
- tests/unit/strata/test_facts.py
- tests/unit/test_ticket_close_bug002_t1438.py
- tests/unit/strata/test_parse.py
- tests/unit/test_ticket_list_summary.py
- tests/unit/test_fleet_runner.py
- tests/unit/test_app_runners_batch7.py
- tests/unit/test_ticket_runner_land_release.py
- tests/unit/test_check.py
- tests/unit/strata/test_export.py
- tests/unit/strata/test_native_staleness.py
- tests/test_coverage_wait_shared.py
- tests/unit/test_lang_strata.py
- tests/test_capability_registry.py
- tests/test_tickets_review.py
- tests/unit/test_parse_runner_direct.py
- tests/unit/test_ticket_close_bug002_t1427.py
- tests/test_graph.py
- tests/unit/test_dup_core.py
- tests/unit/test_app_runners_t0976_mutation_evidence.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_graph_lock.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_land.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_gates_suppress.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_app.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_tickets_collision.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_tickets_evidence_cli.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_check_tool_unavailable.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_conform_eval_needle.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_dup.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_facts.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_ticket_close_bug002_t1438.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_parse.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_ticket_list_summary.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_fleet_runner.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_check.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_export.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_native_staleness.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_coverage_wait_shared.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_lang_strata.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_capability_registry.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_tickets_review.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_parse_runner_direct.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_ticket_close_bug002_t1427.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_graph.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_dup_core.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_app_runners_t0976_mutation_evidence.py
  reason: narrow ticket start's flagged over-broad tests/** to the exact test files
    whose stale OPAQUE001 waiver directive this ticket deletes
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: tests/**
  reason: narrowed to the exact 31 test files touched; the broad glob was flagged
    by ticket start as chronically over-broad
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_vet.py
  reason: 'found during deletion sweep: tests/test_vet.py:4 was also a stale OPAQUE001
    waiver, not caught in the initial 61-directive count'
  actor: logan
  at: '2026-08-06'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/unit/test_dup_core.py::test_core_unavailable_path_is_err_not_exception
- cmd:bash -c "uv run --frozen frob check . --only opaque 2>&1 | grep -q \"0 errors\""
  exit=0 sha256=e3b0c44298fc
designated_repro_test: null
threat: null
component: null
---
T-1659 fixed OPAQUE001's lexical substring matching (raw byte-level needle
search for "setattr(", "eval(", etc, with no AST verification) to decide
semantically instead, via _python_bare_call_ok and
_python_sys_modules_write_ok in src/frob/vet/_capability_scan.py. The
finding count went 142 -> 1.

Consequence: 61 frob:waive OPAQUE001 directives now exist across the repo
(counted directly, excluding fixture-string test data and docstring
mentions), and only 24 of them still match a real finding under the fixed
semantic check. The other 37 waive nothing -- they only ever existed to
suppress the OLD lexical false positive (monkeypatch.setattr, model.eval,
_mutation_for_eval, sys.modules reads, etc) and now report WAIVE004
(stale waiver, matches zero findings).

This ticket deletes the 37 obsolete directives, verified individually
against a fresh `frob check --only opaque` run before deletion (not on the
strength of the WAIVE004 report alone), and keeps the 24 that still
legitimately waive a real semantic-check finding.