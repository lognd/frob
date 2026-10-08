+++
id = "01M4D3H2MXY2G59N9ZHPMRA314"
title = "COV001: count C# files as test-capable subjects"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-08T06:34:29Z"
updated = "2026-10-08T06:34:29Z"
scope = ["crates/frob-obligations/src/cov.rs"]
+++

found while working 0R4E5N8: test_capable_files in cov.rs counts only Rust and Python files, so a C# repo reports no COV001 subjects even though C# tests are now detected by is_test_fn and C# call edges exist.
