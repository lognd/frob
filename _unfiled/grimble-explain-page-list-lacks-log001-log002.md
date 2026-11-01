+++
id = "01M64A0BJE1S5242TGFBGE72XN"
title = "grimble explain page list lacks LOG001/LOG002"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-29T17:06:01Z"
updated = "2026-11-01T15:23:30Z"
scope = ["crates/grimble/**"]

[[acceptance]]
text = "Given grimble explain, when listing pages, then LOG001 and LOG002 are present (table covers every generated page)"
bound = false
+++

Found while working ~394FZ5T, pre-existing: explain_cmd::tests::the_table_covers_every_generated_page_of_the_product fails; explain table lacks LOG001/LOG002.
