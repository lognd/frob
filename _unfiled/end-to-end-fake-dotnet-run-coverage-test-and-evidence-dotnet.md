+++
id = "01M62ZVPV0Z5MYVNJE04RXXRNQ"
title = "End-to-end fake-dotnet run_coverage test and [evidence.dotnet] path in the coverage plan"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-29T04:49:28Z"
updated = "2026-10-29T04:49:28Z"
scope = ["crates/frob-evidence/tests/coverage_csharp.rs"]
+++

Split from 5GRB80B: no end-to-end run_coverage test for C# since required_tool uses which and unsafe set_var is forbidden; also honor [evidence.dotnet] path.
