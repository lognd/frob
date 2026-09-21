---
id: T-3964
title: dataset construct under store with append_only attribute
state: done
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-3942
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_models.py
- src/frob/strata/_dataset.py
- tests/test_dataset_construct.py
- docs/strata/dataset-construct.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_dataset.py
  reason: 'new dataset construct module (parent_store=/append_only attrs + SYS118),
    per accepted design: zero grammar/_models.py change needed'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/test_dataset_construct.py
  reason: tests for dataset construct
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/strata/dataset-construct.md
  reason: 'standalone doc row: docs/modules/gates.md leased'
  actor: logan
  at: '2026-09-19'
evidence:
- tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_parent_store_parses_attr
- tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_parent_store_none_when_absent
- tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_is_dataset_true_with_parent_store
- tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_is_dataset_false_without_parent_store
- tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_is_append_only_true
- tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_is_append_only_false
- tests/test_dataset_construct.py::TestDatasetIndependentCarries::test_dataset_carries_independent_of_parent_store
- tests/test_dataset_construct.py::TestSys118DanglingParentStore::test_dangling_parent_store_fires_sys118
- tests/test_dataset_construct.py::TestSys118DanglingParentStore::test_existing_parent_store_does_not_fire_sys118
- tests/test_dataset_construct.py::TestSys118DanglingParentStore::test_node_without_parent_store_does_not_fire_sys118
designated_repro_test: null
acceptance:
- text: given a design note describing the dataset construct's grammar, its own carries()
    scope, and how append_only is resolved (SYS100 or a new sibling rule), when this
    ticket's design step completes, then the note is attached before implementation
    begins
  evidence:
  - tests/test_dataset_construct.py::TestSys118DanglingParentStore::test_dangling_parent_store_fires_sys118
- text: given the design is accepted, when implemented, then a dataset nested under
    a store can declare carries() independent of the parent store and an append_only
    attribute that a gate can check
  evidence:
  - tests/test_dataset_construct.py::TestDatasetIndependentCarries::test_dataset_carries_independent_of_parent_store
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-177 (T-3942 item 3). Also T-3919 item 5 in that epic's own numbering (finer PII granularity: carries() attaches atoms to a WHOLE STORE today, so a password hash into an audit log and an email into a Redis key are invisible -- both stay inside a node already cleared for the atom). File once here; do not duplicate on T-3919, cite this one instead.

VERIFIED: grepped design/*.strata and design/litmus/*.strata for a dataset construct or an append_only attribute -- none found; `frob ticket new --help` (the closest thing to a language surface check available without deep strata-model reading) shows no such concept either. Today strata models postgres (or any store) as ONE store with ONE capability surface; there is no way to declare "this dataset is append-only from this node" or "this atom is carried only in this sub-region of the store."

FINDING THIS WOULD HAVE CAUGHT (per the consumer, closes four findings across two audits at the root):
- an audit/evidence dataset that must be append-only, with no way for strata to say so
- PII atoms (password hash, email) attached at whole-store granularity, invisible once the store is already cleared for the atom generally

THE MOST STRUCTURAL ITEM in this delta, and the one most clearly ours rather than theirs. Proposed: a `dataset` construct nested under a `store`, carrying its own `carries()` declarations independent of the parent store's, plus an `append_only` attribute resolved by SYS100 (or a new SYS10x sibling). This is a strata LANGUAGE change (new construct, new resolution logic), not a gate rule -- scope and review it as such, separate from any pure-gate work in this same epic.