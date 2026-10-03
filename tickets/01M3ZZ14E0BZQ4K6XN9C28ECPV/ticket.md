+++
id = "01M3ZZ14E0BZQ4K6XN9C28ECPV"
title = "Version scheme: v2 continues 0.53X.0; 1.0.0 is the first stable release"
type = "docs"
category = "in-progress"
priority = "high"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T04:05:51Z"
updated = "2026-10-03T04:05:51Z"
idempotency_key = "m2-version-scheme-053x"
labels = ["milestone:2"]
scope = ["docs/design/**"]

[[acceptance]]
text = "Given releases.md, when read, then the version scheme is 0.53X.0 with 1.0.0 stable and the milestone list uses those versions"
bound = false
+++

Owner decision 2026-10-03: frob v2 releases continue the existing PyPI line as 0.532.0, 0.533.0, ... (lockstep across crates.io and PyPI); 1.0.0 is the first stable version. Update releases.md 5 and 7 and D83.
