+++
id = "01M1QDTV2ME09KEMQF20H92F01"
title = "post-r7 coverage stamp refresh"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:03Z"
aliases = ["crunk:T-0084"]
labels = ["component:crunk", "source:crunk"]
scope = ["frob-coverage.lock.json"]

[[acceptance]]
text = "given main after the r7 lands, when frob check runs, then TEST006/PRE/SCOPE are clean"
bound = true
+++

The r7 land squashes shifted stamped-file hashes; this attributes the main-side stamp refresh commit.
