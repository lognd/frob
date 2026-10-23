+++
id = "01M5HM3W7MK7255AGEN27SXEXP"
title = "CRAFT voice file presence: design/content/voice.toml required when scenes use copy keys (pairs SLOP060)"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4CXT3N608HMB1A77VTT4YXX"
reporter = "lognd"
created = "2026-10-22T10:57:08Z"
updated = "2026-10-23T01:41:03Z"
scope = ["crates/crunk-rules/**", "docs/reference/rules/**", "crates/crunk-check/tests/**", "crates/crunk/tests/**"]

[[acceptance]]
text = "Given scenes using copy keys and no design/content/voice.toml, when crunk check runs, then a CRAFT rule reports the missing voice file and names SLOP060"
bound = false

[[acceptance]]
text = "Given the voice file exists, when crunk check runs, then that rule reports nothing"
bound = false
+++

found while working ~DTBY8Q0; cut from its scope
