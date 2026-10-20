+++
id = "01M4CXRA570ABD65ZDFAFVVZ8Y"
title = "crunk new and crunk edit --patch: id-addressed RFC 6902 edits validated by schema, returning the diff and findings of touched nodes"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXR6ER06SRMEJGSZ20JD5Q"
reporter = "lognd"
created = "2026-10-08T04:53:41Z"
updated = "2026-10-08T04:53:41Z"
scope = ["changelog.d/**", "crates/crunk/**", "crates/crunk-spec/**"]

[[acceptance]]
text = "Given an edit patch, when applied, then the file changes atomically, an invalid patch is refused with the schema error, and the output lists findings for the touched ids only"
bound = false
+++

docs/design/crunk.md section 5.
