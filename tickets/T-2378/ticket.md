---
id: T-2378
title: Decompose and burn frob-dup (exact+renamed) WARN findings to zero, then promote
  to error
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_source.py
- src/frob/vet/_ecosystem.py
- src/frob/vet/_supplychain.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_source.py
  reason: extract shared _read_text_or_empty (frob-dup exact-duplicate T-2378)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_ecosystem.py
  reason: extract shared _read_text_or_empty (frob-dup exact-duplicate T-2378)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_supplychain.py
  reason: extract shared _read_text_or_empty (frob-dup exact-duplicate T-2378)
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
acceptance:
- text: given the family's WARN codes, when frob check --json runs, then zero findings
    remain
  evidence: []
- text: given the family's gate module, when its severity is read, then it is ERROR
    not WARNING
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral), tool `frob-dup`, 2026-08-18: 457 WARN-tier findings
(457 = 'exact' + 'renamed' duplicate-code categories combined).

This is a large campaign, not a single-dispatch burn-down -- 457 findings is an
order of magnitude bigger than the small-family children filed alongside this
one. Before dispatching, re-run `uv run frob check --json --budget 500 |
python3 scripts/check_summary.py` (or filter for tool=="frob-dup" in the raw
--json) and group findings by directory/component so this can be split into
several disjoint-scope children -- do not attempt it as one worktree.

Closure is two-part per the epic (T-0969): (1) zero frob-dup WARN findings,
verified the same way, AND (2) frob-dup's dup-detection promoted from warning
to error severity for the categories burned down. Do not promote a category
still carrying findings.
