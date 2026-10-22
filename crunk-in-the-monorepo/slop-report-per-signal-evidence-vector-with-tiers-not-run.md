+++
id = "01M4CXTBPEVSYD93X6S90ZRDZ9"
title = "Slop report: per-signal evidence vector with tiers not run, never a single opaque score"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M4CXT3N608HMB1A77VTT4YXX"
reporter = "lognd"
created = "2026-10-08T04:54:48Z"
updated = "2026-10-22T09:40:59Z"
scope = ["changelog.d/**", "crates/crunk/**"]

[[acceptance]]
text = "Given crunk check --report slop, when run, then the output lists every signal with evidence and tier, and no aggregate without its parts"
bound = true
+++

deslop research proposal 4.
