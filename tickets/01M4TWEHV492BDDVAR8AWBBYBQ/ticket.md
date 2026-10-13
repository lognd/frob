+++
id = "01M4TWEHV492BDDVAR8AWBBYBQ"
title = "gob-mdtest: marker position must come from the hit, not the first comment token (CI red on corpora)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-13T15:00:14Z"
updated = "2026-10-13T15:14:28Z"
idempotency_key = "mdtest-marker-at"
scope = ["crates/gob-mdtest/**", "changelog.d/**"]

[[acceptance]]
text = "An inline marker after a leading comment on the same line (e.g. an html comment followed by an error marker) attaches to that line, not the next, so the existing corpora parse"
bound = true
+++
