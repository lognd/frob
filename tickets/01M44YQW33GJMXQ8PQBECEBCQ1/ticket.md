+++
id = "01M44YQW33GJMXQ8PQBECEBCQ1"
title = "Project model: .sln and .csproj assemblies mapped to packages"
type = "story"
category = "in-progress"
priority = "high"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:36:59Z"
updated = "2026-10-06T04:09:06Z"
idempotency_key = "d94-sln"
scope = ["crates/gob-symbols/src/dotnet.rs", "crates/gob-symbols/src/paths.rs", "crates/gob-symbols/src/crates.rs", "crates/gob-symbols/src/pipeline.rs", "crates/gob-symbols/tests/dotnet.rs", "docs/design/code-model.md", "docs/reference/config.md"]

[[links]]
kind = "blocked-by"
target = "01M44YQSZ3YEXRDW9RKER9HRA2"

[[acceptance]]
text = "Given a solution with two .csproj files where one has a ProjectReference to the other, when the package graph is built, then each project is a package and the reference is a dependency edge"
bound = false

[[acceptance]]
text = "Given an SDK-style .csproj with default globs and an obj directory, when files are assigned, then source files go to the project and obj/bin files are ignored"
bound = false

[[acceptance]]
text = "Given a malformed .csproj, when frob check runs, then a finding names the file and the project is Unresolved, not skipped"
bound = false
+++

Project discovery in crates/gob-symbols (new dotnet.rs beside crates.rs and paths.rs): parse .sln (project entries, solution folders) and SDK-style and legacy .csproj (Compile globs and default includes, ProjectReference, PackageReference names, RootNamespace, AssemblyName, ImplicitUsings, TargetFramework(s), LangVersion). Each project maps to the existing package/unit notion so ownership, reach and test selection work unchanged; a file belongs to the nearest enclosing project; bin/ and obj/ are ignored. Cross-project references become package dependency edges. Implicit usings from ImplicitUsings feed the import resolution left Unresolved by the calls story. Malformed project files are reported, never dropped. Docs: docs/design/code-model.md package notion section and docs/reference/config.md if a config key is added.
