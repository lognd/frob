+++
id = "01M3Z713RETBN30XBC6CK11FBF"
title = "G07: selectors and select/owner queries in gob-walk"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:24Z"
updated = "2026-10-02T22:36:47Z"
idempotency_key = "m2-selectors"
labels = ["milestone:2"]
scope = ["crates/gob-walk/**", "crates/gob-ir/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z712DPZN71ZQDS6PXY6QQV"

[[links]]
kind = "blocked-by"
target = "01M3Z712GP8XV2WEAS1VHQ7FD4"

[[acceptance]]
text = "Given a selector crates/*/src/** lang=rust kind=fn, when resolved, then it returns the matching units with Must status and excludes markdown"
bound = false
+++

grimble review and grmb-spec: selector grammar (paths, globs, language, kind, attribute predicates) resolved through gob-walk and the scope graph, with May status for globs over units with Unknown edges; owner(path) query; used by ownership and leases.
