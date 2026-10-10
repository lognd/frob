+++
id = "01M4FH86F1XAWKC7KQZSH5B4JE"
title = "Rust adapter: a // frob:doc line between a /// doc block and its item hides the doc comment (false DOC001)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T05:12:53Z"
updated = "2026-10-10T20:01:40Z"
labels = ["adoption:logand-app"]
scope = ["crates/gob-symbols/**", "crates/gob-languages/**", "crates/frob-obligations/**", "changelog.d/**"]

[[acceptance]]
text = "Given /// docs, then // frob:doc path#anchor, then pub fn f, when frob check runs, then f has its doc comment and no DOC001 fires; the directive still binds to f"
bound = false
+++

logand.app-v2 F-544: 26 false DOC001 in wasm-engine.
