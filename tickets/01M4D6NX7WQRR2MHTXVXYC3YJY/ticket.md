+++
id = "01M4D6NX7WQRR2MHTXVXYC3YJY"
title = "Stub-gh test for the land CI tip selection (remote-tracking ref first, local tip fallback)"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 1
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T07:29:39Z"
updated = "2026-10-11T16:36:31Z"
scope = ["changelog.d/**", "crates/frob-land/**"]

[[acceptance]]
text = "Given a stub gh and both ref states, when the gate runs, then it queries the expected commit"
bound = true
+++

Follow-up from ~GHMWDGG.
