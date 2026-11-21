+++
id = "01M7XXCT68PZ5DA86TY2TYMRJR"
title = "Ledger blob reads have no size cap: a huge or hostile ticket blob is read whole into memory"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-21T02:01:35Z"
updated = "2026-11-21T02:01:35Z"
labels = ["no-story"]
scope = ["crates/frob-ledger/**"]

[[acceptance]]
text = "Given a ledger blob larger than the cap, when it is read, then the read fails with a typed error naming the cap and nothing larger than the cap is buffered"
bound = false

[[acceptance]]
text = "Given blobs under the cap, when read, then behavior is unchanged"
bound = false
+++

Audit 2026-11-20 deferred item. no-story: audit follow-up.
