+++
id = "01M6DWWD6MAFPHNBN1HBBBQZCJ"
title = "grimble explain_cmd PAGES table lacks generated rule pages (AMB004/008/009, PLAN012-027, SYS015/016, MDL012 order)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-02T10:29:04Z"
updated = "2026-11-02T10:40:15Z"
scope = ["crates/grimble/src/explain_cmd.rs"]

[[acceptance]]
text = "explain_cmd PAGES lists every generated grimble rule page"
bound = false
+++

explain_cmd::tests::the_table_covers_every_generated_page_of_the_product is red: PAGES lacks AMB004, AMB008, AMB009, PLAN012, PLAN013, PLAN014, PLAN015, PLAN018, PLAN027, SYS015, SYS016 vs docs/reference/rules. Found while working ~EJSH114; regenerate the page list.
