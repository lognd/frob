+++
id = "01M3Z712ZXXKVJYREYG65P3P35"
title = "frob-obligations DOC002 fence tracking ignores fence length"
type = "bug"
category = "todo"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:23Z"
updated = "2026-10-03T06:13:16Z"
idempotency_key = "m2-doc002"
labels = ["milestone:2", "release:0.532.0"]
scope = ["crates/frob-obligations/**"]

[[acceptance]]
text = "Given a four-backtick block containing a three-backtick fence, when DOC002 scans the file, then links inside the outer block are not checked"
bound = false
+++

doc.rs toggles code fences by character without checking fence length, so a triple-backtick fence inside a four-backtick fence ends the outer fence early (found by T-0025). Track fence char and length per CommonMark; add corpus cases.
