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
updated = "2026-10-09T22:35:30Z"
scope = ["crates/frob-land/**", "changelog.d/**", "crates/frob-check/src/scope.rs"]

[[acceptance]]
text = "Given the fast-lands epic design, when this lands, then the behaviour in the title holds with a test"
bound = false

[[acceptance]]
text = "Given other lands advance the base while a land's check runs, when the new base commits touch nothing in the ticket's affected cone (ledger-only commits included), then the land does not re-check and does not go E-LAND-STALE; only commits touching the cone force a re-check, so --wait 120 suffices on a busy repository (logand F-565)"
bound = false
+++
