+++
id = "01M4D3H2MXY2G59N9ZHPMRA314"
title = "COV001: count C# files as test-capable subjects"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-08T06:34:29Z"
updated = "2026-10-09T15:06:38Z"
labels = ["creates:crates/frob-obligations/tests/csharp.rs"]
scope = ["crates/frob-obligations/src/cov.rs", "crates/frob-obligations/tests/csharp.rs"]

[[acceptance]]
text = "Given a repository with C# sources and no C# tests, when frob check runs, then COV001 counts the C# files as test-capable subjects and reports the untested ones"
bound = false
+++

found while working 0R4E5N8: test_capable_files in cov.rs counts only Rust and Python files, so a C# repo reports no COV001 subjects even though C# tests are now detected by is_test_fn and C# call edges exist.
