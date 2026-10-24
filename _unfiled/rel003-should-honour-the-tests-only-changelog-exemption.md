+++
id = "01M5NWA3HFZWBJWZ11VN8JRN7F"
title = "REL003 should honour the tests-only changelog exemption"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-24T02:37:18Z"
updated = "2026-10-24T04:34:46Z"
scope = ["crates/frob-check/src/product.rs", "crates/frob-check/tests/it/check.rs"]

[[acceptance]]
text = "Given a tests-only branch diff and a ticket type listed in pm.changelog_tests_only_types, when frob check --ticket runs, then REL003 does not fire for the missing fragment"
bound = true
+++

found while working ~11PE6E1: rel003_missing only knows type_exempt; it should consult frob_evidence::done::branch_is_tests_only and PmTable::changelog_tests_only.
