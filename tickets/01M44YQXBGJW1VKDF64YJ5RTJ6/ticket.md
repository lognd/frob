+++
id = "01M44YQXBGJW1VKDF64YJ5RTJ6"
title = "C# test selection in frob test"
type = "story"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:37:01Z"
updated = "2026-10-08T14:17:08Z"
idempotency_key = "d94-select"
scope = ["crates/frob-tests/**", "crates/gob-testsupport/src/lib.rs", "docs/reference/cli/**", "docs/design/build-test-ci.md"]

[[links]]
kind = "blocked-by"
target = "01M44YQV7C3FYXB3QH20R4E5N8"

[[links]]
kind = "blocked-by"
target = "01M44YQW33GJMXQ8PQBECEBCQ1"

[[links]]
kind = "blocked-by"
target = "01M44YQWY2SWCH7PS9F9W0WEA9"

[[acceptance]]
text = "Given a change to a C# method reached by two tests in one .csproj, when frob test runs, then exactly those tests are selected and run through the dotnet provider"
bound = true

[[acceptance]]
text = "Given a change to a method no test reaches, when frob test runs, then no test is selected and the gap is reported"
bound = true

[[acceptance]]
text = "Given a touched file in a Unity asmdef assembly and no unity provider yet configured, when frob test runs, then the selection is printed and the run refuses with a remedy"
bound = true
+++

frob test (crates/frob-tests: select.rs, reach.rs, touched.rs, catalog.rs, run.rs, rule.rs, verb.rs) maps touched C# symbols to test ids through the same reach graph as Rust and Python: a TestTarget for C# carries the project (csproj or asmdef assembly) and the fully qualified test name, and the runner is chosen by project kind (dotnet for .csproj projects; the unity provider for asmdef assemblies, wired by the unity evidence story, until then reported as a refusal with a remedy). Touched C# files in a partial type select tests reaching any part. Docs: docs/reference/cli (frob test) and docs/design/build-test-ci.md.
