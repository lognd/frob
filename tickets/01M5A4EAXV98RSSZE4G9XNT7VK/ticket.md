+++
id = "01M5A4EAXV98RSSZE4G9XNT7VK"
title = "Run the live GitHub listing probe (live_created_issue_appears_in_listing_at_once) with a token"
type = "task"
category = "todo"
priority = "medium"
parent = "01M4052QWSEERAG3JPCGXM4RK4"
reporter = "lognd"
created = "2026-10-19T13:08:32Z"
updated = "2026-10-19T13:08:32Z"

[[acceptance]]
text = "The ignored live probe passes against a real repository and is bound as evidence."
bound = false
+++

GXM4RK4 landed with its live-verification criterion unbound because no token was available. Run: FROB_GH_PROBE_LISTING and FROB_GH_PROBE_NUMBER set, cargo test -p frob-mirror live_created_issue_appears_in_listing_at_once -- --ignored. Record result and fix the listing lookup if it fails.
