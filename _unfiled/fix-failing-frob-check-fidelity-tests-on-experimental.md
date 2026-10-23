+++
id = "01M5KQCAD16D6T307SXYNP04N0"
title = "Fix failing frob-check fidelity tests on experimental"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-23T06:32:39Z"
updated = "2026-10-23T06:37:27Z"
scope = ["crates/frob-check/**"]

[[acceptance]]
text = "fidelity::a_partial_markdown_parse_points_at_the_table_row_and_names_the_cause and fidelity::not_applicable_is_counted_never_a_finding pass"
bound = false
+++

Both fail on experimental at 2e4f79a3ef (fidelity.rs lines 121 and 156), independent of the CI003 retirement. Found while landing ~TXCDEKR.
