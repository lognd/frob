---
id: T-4663
title: 'Wire [arch.layering] into frob check: ARCH10x red on a kernel layering violation'
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4656
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_layering.py
- frob.toml
- tests/unit/test_layering_gate.py
- docs/modules/arch.md
- src/frob/gates/_arch.py
- frob-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_arch.py
  reason: wiring check_layering_edges into frob check requires calling it from the
    ARCH gate module; layering.py alone cannot invoke frob check
  actor: logan
  at: '2026-09-19'
- op: add
  glob: frob-ratchet.lock.json
  reason: baselining T-4663's own measured 30 pre-existing ARCH104 dip-layering-violation
    edges via frob pool snapshot, per brief instruction to ratchet rather than waive
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_layering_gate.py::test_upward_import_is_arch10x_red
- tests/unit/test_layering_gate.py::test_layering_job_reports_edges_checked
- tests/unit/test_layering_gate.py::test_no_declared_layering_config_is_not_a_violation
- tests/unit/test_layering_gate.py::test_allowed_edge_across_declared_layers_is_not_arch104
designated_repro_test: null
acceptance:
- text: Given [arch.layering] declares ledger < leases < land < app with gates independent,
    when `frob check` runs, then a layering violation is reported as an ARCH10x finding
    at RED severity and fails the check.
  evidence:
  - tests/unit/test_layering_gate.py::test_upward_import_is_arch10x_red
  - tests/unit/test_layering_gate.py::test_layering_job_reports_edges_checked
  - tests/unit/test_layering_gate.py::test_no_declared_layering_config_is_not_a_violation
  - tests/unit/test_layering_gate.py::test_allowed_edge_across_declared_layers_is_not_arch104
- text: 'POSITIVE CONTROL: tests/unit/test_layering_gate.py::test_upward_import_is_arch10x_red
    plants an import from the ledger layer back up into the land layer and asserts
    `frob check` reports ARCH10x at red. It FAILS on dev today (the layering checker
    is never invoked, so the planted violation is reported by nothing -- a silent
    zero) and passes after this leaf.'
  evidence:
  - tests/unit/test_layering_gate.py::test_upward_import_is_arch10x_red
  - tests/unit/test_layering_gate.py::test_layering_job_reports_edges_checked
  - tests/unit/test_layering_gate.py::test_no_declared_layering_config_is_not_a_violation
  - tests/unit/test_layering_gate.py::test_allowed_edge_across_declared_layers_is_not_arch104
- text: Given no violation, when `frob check` runs, then the layering job reports
    a nonzero number of edges CHECKED, never a bare zero; tests/unit/test_layering_gate.py::test_layering_job_reports_edges_checked
    proves the job actually ran.
  evidence:
  - tests/unit/test_layering_gate.py::test_upward_import_is_arch10x_red
  - tests/unit/test_layering_gate.py::test_layering_job_reports_edges_checked
  - tests/unit/test_layering_gate.py::test_no_declared_layering_config_is_not_a_violation
  - tests/unit/test_layering_gate.py::test_allowed_edge_across_declared_layers_is_not_arch104
- text: docs/modules/arch.md's DIP layering section is updated to describe the live
    kernel contract rather than an inert example, in this same change.
  evidence:
  - tests/unit/test_layering_gate.py::test_upward_import_is_arch10x_red
  - tests/unit/test_layering_gate.py::test_allowed_edge_across_declared_layers_is_not_arch104
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4663
branch: t-4663
---
Kernel decoupling leaf (LAYERING story). ~3 points. This is the leaf that makes the whole epic irreversible.

`[arch.layering]` already exists in frob.toml, but T-0620 shipped it INERT: the schema and `frob.arch._layering.check_layering_violations` are real, and nothing calls them from `frob check`. A declared-but-unenforced boundary is not a boundary.

Wire it, and declare the kernel contract in frob.toml:

  layers: ledger = src/frob/tickets/_store*.py-and-successors, leases = the lease store module, land = the land state machine, app = src/frob/app, gates = src/frob/gates
  allow:  leases -> ledger; land -> leases, ledger; app -> land, leases, ledger; gates -> (nothing in the kernel); ledger -> ()

A violation is ARCH10x RED in `frob check`, not a warning. Log every checked edge at DEBUG and every violation at ERROR with both endpoints and the importing line.

Keep the existing app -> lang example contract intact; this leaf ADDS the kernel layers to it.

Note: the exact path globs per layer depend on the module names the sibling ledger/lease/land leaves land. File the contract against the paths that exist when this leaf starts and state any deferred layer in the done report.

## Unblock log
- 2026-09-19: unblocked by T-4657 -- T-4657 is READY and queued to land; blocker is land order only