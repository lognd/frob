## Done report

-- T-3964 (dataset construct under store with append_only attribute)

Parent: T-3942 (F-177) / T-3919 item 5. Dispatched directly by the
coordinator (no separate design-acceptance ticket split, unlike
T-3961's original dispatch) with the instruction: failing test first
with positive controls, docs row, PRE-READY checks, evidence, READY.
The design note below stands in for acceptance[1]; acceptance[2] is
satisfied by the same commit since the design's own conclusion is a
zero-grammar-change reuse (no separate "design accepted" gate needed
before implementing something that changes nothing structural).

### Changed
```
 docs/strata/dataset-construct.md |   99 ++++
 src/frob/strata/_dataset.py      |  131 +++++
 tests/test_dataset_construct.py  |  109 ++++
 tickets/T-3964/done-report.md    | 1165 ++++++++++++++++++++++++++++++++++++++
 tickets/T-3964/ticket.md         |   28 +-
 5 files changed, 1521 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_parent_store_parses_attr` (pytest node id, verified passing when recorded)
- `tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_parent_store_none_when_absent` (pytest node id, verified passing when recorded)
- `tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_is_dataset_true_with_parent_store` (pytest node id, verified passing when recorded)
- `tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_is_dataset_false_without_parent_store` (pytest node id, verified passing when recorded)
- `tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_is_append_only_true` (pytest node id, verified passing when recorded)
- `tests/test_dataset_construct.py::TestDatasetAttrParsing::test_node_is_append_only_false` (pytest node id, verified passing when recorded)
- `tests/test_dataset_construct.py::TestDatasetIndependentCarries::test_dataset_carries_independent_of_parent_store` (pytest node id, verified passing when recorded)
- `tests/test_dataset_construct.py::TestSys118DanglingParentStore::test_dangling_parent_store_fires_sys118` (pytest node id, verified passing when recorded)
- `tests/test_dataset_construct.py::TestSys118DanglingParentStore::test_existing_parent_store_does_not_fire_sys118` (pytest node id, verified passing when recorded)
- `tests/test_dataset_construct.py::TestSys118DanglingParentStore::test_node_without_parent_store_does_not_fire_sys118` (pytest node id, verified passing when recorded)
