+++
id = "01M4FD31PPJCEBG5G351FSGW5S"
title = "ticket evidence add --provider has no dotnet or unity choice although [evidence.dotnet] exists and the dotnet provider landed"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T04:00:10Z"
updated = "2026-10-10T00:44:05Z"
labels = ["adoption:hullbreach", "creates:crates/frob-evidence/tests/providers.rs"]
scope = ["changelog.d/**", "crates/frob-evidence/src/record.rs", "crates/frob-evidence/src/verbs.rs", "crates/frob-evidence/src/error.rs", "crates/frob-evidence/tests/providers.rs"]

[[acceptance]]
text = "Given a C# repository, when frob ticket evidence add --provider dotnet runs with a TRX-producing command, then the TRX is parsed into evidence; the --provider value list is generated from the provider registry so a new provider is never missing"
bound = true

[[acceptance]]
text = "Given no [evidence] allowed_tools in frob.toml, when frob config show runs, then the default includes dotnet as config.md and the quickstart state, and a test pins the default list to the documented one"
bound = true
+++

Hullbreach game repro (B).
