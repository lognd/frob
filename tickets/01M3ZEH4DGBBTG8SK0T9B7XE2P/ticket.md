+++
id = "01M3ZEH4DGBBTG8SK0T9B7XE2P"
title = "grmb-spec corrections from the G08 implementation"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T23:17:29Z"
updated = "2026-10-02T23:25:53Z"
idempotency_key = "m2-grmb-spec-fixes"
labels = ["milestone:2"]
scope = ["docs/design/**"]

[[acceptance]]
text = "Given grmb-spec.md, when compared with the G08 report's defect list, then each defect is resolved in the text and D-c to D-g appear as decision rows"
bound = true
+++

From ~63XJMC3: fix the seven spec defects it lists (facet table vs encoding table; transport atoms; bare CR as opaque binary; MDL006 vs MDL014; MDL015 wording; multi-file corpus cases as directories; MDL012 second half needs lock data) and record its proposed decisions D-c to D-g (file item order, top-level accept placement, doc comments as attr(doc), pack module attrs, Sig facet superset for contract and flow) as README decision rows.
