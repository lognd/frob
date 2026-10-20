+++
id = "01M4CXQYFA9ACDVWF4R62C50FH"
title = "crunk import dtcg and export dtcg round-trip"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-08T04:53:29Z"
updated = "2026-10-08T04:53:29Z"
scope = ["changelog.d/**", "crates/crunk-tokens/**", "crates/crunk/**"]

[[acceptance]]
text = "Given a DTCG file, when imported and exported, then the result equals the input up to key order"
bound = false
+++

docs/design/crunk.md section 5.
