+++
id = "01M5NFNV870VQSGDJAT79HY9GP"
title = "explain_cmd PAGES lacks COV004, DOC003 and DOC006"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-23T22:56:31Z"
updated = "2026-10-23T23:30:51Z"
scope = ["crates/frob/src/explain_cmd.rs"]

[[acceptance]]
text = "Given explain_cmd PAGES, when the test the_table_covers_every_generated_page_of_the_product runs, then it passes with COV004, DOC003 and DOC006 listed"
bound = true
+++
