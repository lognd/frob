+++
id = "01M6DB71PMV9KJQPW66EJSH114"
title = "grimble tests red on experimental: explain_cmd PAGES lacks AMB004/008/009, graph PLAN006 test, design_docs moved paths"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-02T05:20:18Z"
updated = "2026-11-02T10:31:23Z"
scope = ["crates/grimble/tests/graph.rs", "crates/grimble-check/tests/design_docs.rs"]

[[acceptance]]
text = "the 3 grimble tests pass without loosening"
bound = true
+++

Found while working ~V82CNAR; all fail without its changes. (1) grimble explain_cmd::tests::the_table_covers_every_generated_page_of_the_product: PAGES lacks AMB004/AMB008/AMB009. (2) grimble tests/graph.rs plan006_fires_for_an_uncovered_pair...: no PLAN006 for '-!> end ok' scenario. (3) grimble-check tests/design_docs.rs reads docs/design/grmb-spec.md and binding.md, which moved.
