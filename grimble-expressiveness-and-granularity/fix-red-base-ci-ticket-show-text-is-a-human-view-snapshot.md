+++
id = "01M6NX3AS986KQDP6YT30HTC3F"
title = "Fix red base CI: ticket_show_text_is_a_human_view snapshot and grimble the_table_covers_every_generated_page_of_the_product"
type = "bug"
category = "in-progress"
priority = "critical"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-05T13:06:47Z"
updated = "2026-11-05T13:31:15Z"
scope = ["crates/frob/tests/**,crates/grimble-check/tests/**,crates/frob/src/snapshots/**", "crates/grimble/src/explain_cmd.rs", "crates/frob/tests/it/snapshots/**"]

[[acceptance]]
text = "Both tests pass on experimental: the insta snapshot is accepted or the output fixed, and the grimble generated-page table covers every page"
bound = true
+++
