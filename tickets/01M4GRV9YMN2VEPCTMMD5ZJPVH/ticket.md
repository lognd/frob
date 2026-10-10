+++
id = "01M4GRV9YMN2VEPCTMMD5ZJPVH"
title = "Land checks the affected cone: touched files plus dependency cone for frob rules, Unknown edges included"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4GRTA9XBJCM2RY98HWZXYC7"
reporter = "lognd"
created = "2026-10-09T16:44:53Z"
updated = "2026-10-10T02:19:15Z"
scope = ["changelog.d/**", "crates/frob-check/src/product.rs", "crates/frob-check/src/scope.rs", "crates/frob-check/src/lib.rs", "crates/frob-check/tests/check.rs", "crates/frob-land/src/land.rs", "crates/frob-land/src/ratchet.rs"]

[[acceptance]]
text = "Given the fast-lands epic design, when this lands, then the behaviour in the title holds with a test"
bound = true

[[acceptance]]
text = "Given other lands advance the base while a land's check runs, when the new base commits touch nothing in the ticket's affected cone (ledger-only commits included), then the land does not re-check and does not go E-LAND-STALE; only commits touching the cone force a re-check, so --wait 120 suffices on a busy repository (logand F-565)"
bound = true
+++
