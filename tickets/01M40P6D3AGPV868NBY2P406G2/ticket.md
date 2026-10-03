+++
id = "01M40P6D3AGPV868NBY2P406G2"
title = "GRL lexer: keep strings raw and let the parser decide interpolation by position"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T10:50:41Z"
updated = "2026-10-03T10:50:41Z"
idempotency_key = "m2-grl-lexer-raw-strings"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/**"]

[[acceptance]]
text = 'Given a regex string "a{2" in a where clause, when parsed, then it is a literal string with no error'
bound = false
+++

Limitation from ~MVY3DFK: the lexer splits every string into text and interpolation parts without knowing the position, so an unbalanced { or a {...} containing a quote in a non-message string (a regex string like "a{2" or a glob) fails in the lexer before the parser can treat it as literal; the workaround is \{. Make the lexer emit raw string tokens (escape-checked only) and move interpolation splitting into the parser for message positions only, so non-message strings never fail on braces. Keep spans exact; update malformed cases.
