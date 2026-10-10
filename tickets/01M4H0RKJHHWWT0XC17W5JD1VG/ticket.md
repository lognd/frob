+++
id = "01M4H0RKJHHWWT0XC17W5JD1VG"
title = "DOC rule: every design and guide document carries one status header from a fixed vocabulary (current, draft, superseded-by X, historical, generated); generated docs/README.md index lists every document with its status"
type = "story"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T19:03:13Z"
updated = "2026-10-09T19:03:13Z"
labels = ["docs"]
scope = ["crates/frob-obligations/**", "crates/gob-dev/**", "changelog.d/**"]

[[acceptance]]
text = "Given a docs/ markdown file with no status header, a status outside the vocabulary, or 'superseded-by' naming a missing document, when frob check runs, then a finding names it; the index page is generated and checked by the generated-file gate"
bound = false
+++

Audit: 24 shipped design files still say DRAFT (T-0001); status lines come in 9 spellings; nothing indexes 217 documents.
