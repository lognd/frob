+++
id = "01M3Z713VGKF4Z0JJ3263XJMC3"
title = "G08: grimble-model crate: .grmb parser, printer, fmt and U adapter"
type = "task"
category = "in-progress"
priority = "high"
points = 13
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:24Z"
updated = "2026-10-02T23:15:55Z"
idempotency_key = "m2-grmbmodel"
labels = ["milestone:2"]
scope = ["crates/grimble-model/**", "crates/gob-languages/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z712GP8XV2WEAS1VHQ7FD4"

[[links]]
kind = "blocked-by"
target = "01M3Z713RETBN30XBC6CK11FBF"

[[acceptance]]
text = "Given the corpus from the specification, when parsed, printed and parsed again, then the U terms are identical and every directive in a .grmb file binds to its entity"
bound = false
+++

G01 spec: tree-sitter or hand-written parser for .grmb, error recovery, alpha-normal printer (grimble fmt), the F4 U adapter so frob directives bind to entities, conformance corpus.
