+++
id = "01M7XM0RBF5FGQJEGSVTARVX8M"
title = "Redaction of key: value and JSON forms corrupts tool stdout that frob-check parses"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-20T23:17:42Z"
updated = "2026-11-20T23:17:42Z"
labels = ["no-story"]
scope = ["crates/gob-log/**", "crates/gob-exec/**"]

[[acceptance]]
text = "Given a tool whose JSON stdout has a key field holding an object, when the runner redacts stdout, then the JSON is unchanged and still parses"
bound = false

[[acceptance]]
text = "Given a quoted secret value in key: value or JSON form, when redacted, then the quotes are kept so the output stays valid JSON"
bound = false
+++

Regression from 4528598984 (~PAD8WST): the new JSON/colon redaction rule mangles zizmor output such as {"key":{"Local":...}}, so frob-check tool_bind tests and the CI001/CI003 mdtest corpus fail on ubuntu (CI run 44832765787). Fix: values starting with a brace or bracket are never masked; quoted values keep their quotes. no-story: regression fix.
