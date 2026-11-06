+++
id = "01M6SBWTKDBFRMZE208N57VN6V"
title = "grimble explain table test misses COH004 and TESTQ001-003 pages"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-06T21:23:05Z"
updated = "2026-11-06T22:37:49Z"
scope = ["crates/grimble/src/explain_cmd.rs"]

[[acceptance]]
text = "The explain table covers every generated rule page"
bound = true
+++

explain_cmd::tests::the_table_covers_every_generated_page_of_the_product fails: the generated page list has COH004 and TESTQ001-003 that the explain table lacks. Seen while working ~9C821MB; not confirmed on base.
