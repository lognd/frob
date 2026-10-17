+++
id = "01M4FDR99VC2BKWKC6WV58QYKH"
title = "Ledger commit volume: coalesce ledger writes per verb invocation and document ref_mode so code branches carry no ledger commits"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-09T04:11:46Z"
updated = "2026-10-17T06:41:19Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob-ledger/**", "docs/guides/**", "changelog.d/**"]

[[acceptance]]
text = "Given one verb that writes several events (update plus comment), when it runs, then exactly one ledger commit is made"
bound = true

[[acceptance]]
text = "Given ref_mode set to a ticket ref (~H3WVSYM), when four tickets are worked on a code branch, then that branch contains no ledger commits, and the getting-started guide says so"
bound = true
+++
