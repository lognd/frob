---
id: T-2956
title: 'frob-dup: triage src/frob/gates renamed-duplicate cluster (20 groups)'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: T-2378
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_arch_schema.py
- src/frob/gates/_docblocks.py
- src/frob/gates/_docblocks_schema.py
- src/frob/gates/_flag_coverage.py
- src/frob/gates/_gates_schema.py
- src/frob/gates/_native_schema.py
- src/frob/gates/_profile_schema.py
- src/frob/gates/_refs_schema.py
- src/frob/gates/_test_runner_schema.py
- src/frob/gates/_testing_schema.py
- src/frob/gates/_toplevel_scalar_schema.py
- tickets/T-2956/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/**
  reason: triage disposition applies frob:waive DUP001 directives inside src/frob/gates
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: src/frob/gates/**
  reason: narrowing to actually-touched files
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/__init__.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_arch_schema.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_docblocks.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_docblocks_schema.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_flag_coverage.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_gates_schema.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_native_schema.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_profile_schema.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_refs_schema.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_test_runner_schema.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_testing_schema.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_toplevel_scalar_schema.py
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2956/**
  reason: schema-family frob:waive directives + ticket ledger
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
acceptance:
- text: given the src/frob/gates frob-dup cluster measured in this ticket's body,
    when triaged, then every group is either extracted, waived with a reason, or covered
    by a documented detector-narrowing decision
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed as a T-2378 sibling per the "decompose, do not mega-land" instruction.

Cluster (frob-dup, unscoped, measured 2026-08-26): 20 renamed-duplicate
groups whose fragments live in src/frob/gates. The largest sub-cluster (4
groups: 44/21/17/11-line blocks) spans the T-2390-epic "*_schema.py"
config-validation family (_refs_schema.py, _arch_schema.py,
_test_runner_schema.py, _gates_schema.py, _native_schema.py,
_toplevel_scalar_schema.py, _docblocks_schema.py, _profile_schema.py,
_testing_schema.py) -- these files' own docstrings say they deliberately
copy one established pattern per config table (T-2390's own words: "this
module is the missing check... establishing the pattern the epic's other
nine children copy"). That family is very likely a NARROW-THE-DETECTOR or
WAIVE case, not an extraction -- forcing a shared base would couple
independently-evolving per-table validators, which is exactly what T-2390
avoided on purpose. Judgment call for whoever works this: read each
_schema.py docstring before deciding waive vs extract.

The remaining ~16 groups in this cluster are NOT pre-triaged -- scattered
across _port_selfcheck.py, _docstatus.py, _docptr.py, __init__.py,
_dup_graph_schema.py, _bug_repro.py, _exhaustive_handling.py,
_registry_exhaustiveness.py, _doclink_docanchor.py, _flag_coverage.py,
_walk_lint.py/_render_lint.py, _coverage.py/_baseline.py, and a few
cross-package ones reaching into src/frob/lang, src/frob/vet, src/frob/arch,
src/frob/dup, src/frob/perf, src/frob/deploy, src/frob/app. Decompose
further by file pair/group before dispatching -- do not take this as one
worktree, several of these fragments touch files other live agents may be
leasing.

Re-measure via: uv run frob check --json --only static, filter
tool=="frob-dup", filter messages containing "src/frob/gates".
