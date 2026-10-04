+++
id = "01M2RX0AF5FC9XRDTP2WKJEHVA"
title = "Capability matrix: csharp/net cell is both patterned and excused after Unity net APIs landed (T-4514)"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-18T00:00:00Z"
updated = "2026-09-18T00:00:03Z"
aliases = ["T-4581"]
labels = ["milestone:0.533.0"]
scope = ["src/frob/vet/_capability_registry/_matrix.py", "tests/test_capability_registry.py"]

[[acceptance]]
text = "bound(['tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_cell_is_both_patterned_and_excused', 'tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells']): the generated csharp/net excuse is removed and no matrix cell is both patterned and excused, while every cell remains patterned or excused"
bound = false
+++

## Drop reason
- 2026-09-21: T-4514's land already removed the stale generated csharp/net excuse; TestMatrixExhaustiveness passes unmodified against current dev, nothing left to fix (absorbed by T-4514)
