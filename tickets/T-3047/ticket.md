---
id: T-3047
title: 'Type-checked code review and decision records: review as a graph node with
  provenance, decisions carrying their reason as data'
state: in-progress
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-3004
tier: ticket
sprint: strata-vmodel
runs_last: false
milestone: 0.535.0
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-3047
branch: t-3047
scope:
- strata-core/src/graph/model.rs
- strata-core/src/graph/vmodel/mod.rs
- tests/unit/strata/test_vmodel_review_decision.py
- tests/unit/strata/test_vmodel_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/graph/model.rs
  reason: review and decision nodes with reason as data
  actor: logan
  at: '2026-09-23'
- op: add
  glob: strata-core/src/graph/vmodel/mod.rs
  reason: review and decision nodes with reason as data
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/strata/_selfconform_models.py
  reason: review and decision nodes with reason as data
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/strata/test_vmodel_check.py
  reason: review and decision nodes with reason as data
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/strata/vmodel.md
  reason: review and decision nodes with reason as data
  actor: logan
  at: '2026-09-23'
- op: remove
  glob: tests/unit/strata/test_vmodel_check.py
  reason: collides with T-3010's live lease (already covers recorded evidence, cannot
    be freed); using a new sibling test file instead
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/strata/test_vmodel_review_decision.py
  reason: sibling test file avoiding the test_vmodel_check.py collision with T-3010's
    live lease
  actor: logan
  at: '2026-09-24'
- op: remove
  glob: docs/strata/vmodel.md
  reason: collides with T-3010's live lease on this file; document review/decision-reason
    in docs/modules/gates.md-adjacent location or defer cross-link until T-3010 lands
  actor: logan
  at: '2026-09-24'
- op: remove
  glob: src/frob/strata/_selfconform_models.py
  reason: wrong module -- SYS100-102 self-conformance is unrelated; decision/review-node
    reason enforcement is entirely Rust-side construction-time validation, no Python
    schema module needed
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/strata/test_vmodel_check.py
  reason: T-3010's lease released; apply the saved fix for decision nodes now requiring
    reason (scratchpad/t3047-fix-for-t3010-test_vmodel_check.patch) so the schema
    change does not break dev
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3004
  reason: 'owner directive 2026-08-26: type-checked reviews/decisions, no monofiles
    with graph-checked hyperlinking, and normalized record shapes are all part of
    the strata software-engineering engine'
  actor: logan
  at: '2026-08-26'
- field: milestone
  old_value: 1.1.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: sprint
  old_value: null
  new_value: strata-vmodel
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '8'
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/strata/test_vmodel_review_decision.py::TestDecisionNodeRequiresReason::test_fires_a_construction_error_on_a_bare_decision_node
- tests/unit/strata/test_vmodel_review_decision.py::TestDecisionNodeRequiresReason::test_quiet_when_reason_is_present
- tests/unit/strata/test_vmodel_review_decision.py::TestReviewNodeRequiresCommitAndReason::test_fires_on_a_bare_review_node
- tests/unit/strata/test_vmodel_review_decision.py::TestReviewNodeRequiresCommitAndReason::test_quiet_when_commit_and_reason_are_present
- tests/unit/strata/test_vmodel_review_decision.py::TestSupersedesRoundTrip::test_reasoned_supersedes_edge_between_two_decisions_round_trips
- tests/unit/strata/test_vmodel_review_decision.py::TestSupersedesRoundTrip::test_supersedes_edge_missing_reason_is_a_construction_error
- tests/unit/strata/test_vmodel_review_decision.py::TestSupersedesRoundTrip::test_review_node_can_decide_an_artifact
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Unblock log
- 2026-09-23: unblocked by T-5460 -- L0 dropped: edge kinds already landed (T-3007/T-3042)
- 2026-09-24: unblocked by T-3010 -- coordinator directive 2026-09-24: T-3010's own blocked_by edge is sequencing-only (shared graph schema file); building T-3047 on top of t-3010 branch content merged in, diffs kept separable, T-3010 lands independently via its own land