+++
id = "01M4FD17P5R19N6VBBB18H72WH"
title = "frob migrate exceptions: rewrite v1 frob:waive to frob:accept or frob:defer, delete waivers of rules v2 lacks, report each"
type = "story"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 3
parent = "01M4CTTVCB8JJ9JB2NQHQP5ARY"
reporter = "lognd"
created = "2026-10-09T03:59:10Z"
updated = "2026-10-09T16:28:35Z"
labels = ["adoption:hullbreach"]
scope = ["crates/gob-dev/**", "crates/frob/**", "changelog.d/**"]

[[acceptance]]
text = "Given v1 frob:waive comments for an existing rule with a reason, with follow_up, and for a retired rule, when the migration runs, then they become accept, defer and a deletion respectively, each listed in the report"
bound = false
+++

exceptions.md section on migration. Hullbreach platform has 119 waivers (DOC006, OPAQUE001, WIRE001, REF002, TEST001).
