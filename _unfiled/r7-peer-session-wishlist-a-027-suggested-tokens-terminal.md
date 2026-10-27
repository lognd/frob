+++
id = "01M1QDTV28VH1T0HG8P16RJC28"
title = "r7: peer-session wishlist (A-027) -- suggested tokens, terminal preview/diff/explain, roadmap"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:35Z"
aliases = ["crunk:T-0072"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["docs/design/*.md", "docs/design/subsystems/*.md"]

[[acceptance]]
text = "given A-027, when the design tree is read, then the three build-now features have layer-2..4 contracts and the remaining items appear in a Roadmap section"
bound = true
+++

The logand.app-v2 coordinator's 10-item CLI-Figma wishlist (A-027). Build-now trio: structured suggested_token on violations (completes CR-20/A-024's report-as-data), crunk preview + crunk diff (terminal-native token sheets, CR-01/CR-15 refinement), crunk explain <token>. The other seven items are recorded as an explicit Roadmap section with queued tickets, not silently dropped.
