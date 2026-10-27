+++
id = "01M5XD3SXWDQJE0YT8K5GRB80B"
title = "C# coverage via coverlet under the dotnet provider, and Unity editor coverage"
type = "story"
category = "todo"
priority = "high"
points = 5
parent = "01M5XD3SCZ3VFWNYXJC8FPN9FB"
reporter = "lognd"
created = "2026-10-27T00:45:39Z"
updated = "2026-10-27T00:45:39Z"
scope = ["crates/frob-evidence/src/coverage/csharp.rs", "crates/frob-evidence/tests/coverage_csharp.rs"]

[[acceptance]]
text = "Given a test run through the provider with coverage enabled, when it finishes, then a normalised lcov report is written under .git/frob and the coverage figure is recorded on the evidence record"
bound = false

[[acceptance]]
text = "Given a [[coverage.threshold]] scope below its minimum for this language, when frob check runs, then COV004 reports it, and a tool that is missing is reported as not run rather than passing"
bound = false
+++
