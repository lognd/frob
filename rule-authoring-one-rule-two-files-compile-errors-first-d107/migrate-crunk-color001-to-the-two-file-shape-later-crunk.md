+++
id = "01M48R0538K77RY0W3W6AN9XJY"
title = "Migrate crunk COLOR001 to the two-file shape; later crunk rules use only the attribute"
type = "story"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 1
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:08Z"
updated = "2026-10-08T12:35:32Z"
scope = ["crates/crunk-check/**"]

[[links]]
kind = "blocked-by"
target = "01M48R029HFBJ3PKQX5GBBKJ6V"

[[acceptance]]
text = "COLOR001 has a generated docs page"
bound = false

[[acceptance]]
text = "STYLE_TAGS is deleted"
bound = false
+++

M8: COLOR001 in the new shape, STYLE_TAGS gone (applies = languages(css, typescript; needs = [Style])); the crunk rule tickets write new rules in the new shape (no crunk-rules crate). Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
