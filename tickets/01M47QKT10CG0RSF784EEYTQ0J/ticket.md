+++
id = "01M47QKT10CG0RSF784EEYTQ0J"
title = "gob-languages and gob-symbols: HTML grammar and markup adapter"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T04:30:09Z"
updated = "2026-10-06T10:28:08Z"
scope = ["crates/gob-languages/**", "crates/gob-symbols/**"]

[[links]]
kind = "blocked-by"
target = "01M47QKDM2J0EKW2TYH4N35GSV"

[[acceptance]]
text = "HTML fixtures produce markup and style snapshots"
bound = false

[[acceptance]]
text = "script and style elements become region islands with the right language tag"
bound = false

[[acceptance]]
text = "the capability matrix has an html row"
bound = false
+++

language-engines.md section 3. Add the HTML grammar behind a feature in gob-languages with its comment scanner, and an HTML adapter in gob-symbols producing markup (elements, attributes, text), inline style attributes as style, and script/style elements as region islands in js/css.
