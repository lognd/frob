+++
id = "01M5NWA3HFZWBJWZ11VN8JRN7F"
title = "REL003 should honour the tests-only changelog exemption"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-24T02:37:18Z"
updated = "2026-10-24T02:37:18Z"
scope = ["crates/frob-check/src/product.rs"]
+++

found while working ~11PE6E1: rel003_missing only knows type_exempt; it should consult frob_evidence::done::branch_is_tests_only and PmTable::changelog_tests_only.
