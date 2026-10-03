+++
id = "01M3ZM5MB6N0B2HX73PEHMQCXV"
title = "Call qualifiers in the symbol graph so COV001 poison does not flood on common names"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T00:56:04Z"
updated = "2026-10-03T01:58:32Z"
idempotency_key = "m2-call-qualifiers"
labels = ["milestone:2"]
scope = ["crates/gob-symbols/**", "crates/frob-obligations/**"]

[[acceptance]]
text = "Given this repository, when frob check runs, then COV001 Unresolved findings fall below 40 and every remaining one names the ambiguous call"
bound = false
+++

From ~5NFTK3H: COV001 treats any callable whose name matches an unresolved call in a test's reach as Unresolved, so common names (new, run) produce 342 Unresolved findings on this repository. Record the receiver or path qualifier on unresolved call edges in gob-symbols (Type::new vs other::new, self.run vs x.run) and match poison on (qualifier, name) with May only when the qualifier is unknown; target: Unresolved COV001 count on this repository drops by an order of magnitude without hiding any real May edge.
