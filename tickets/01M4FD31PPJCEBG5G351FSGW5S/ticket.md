+++
id = "01M4FD31PPJCEBG5G351FSGW5S"
title = "ticket evidence add --provider has no dotnet or unity choice although [evidence.dotnet] exists and the dotnet provider landed"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T04:00:10Z"
updated = "2026-10-09T04:00:10Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob-evidence/**", "crates/frob/**", "changelog.d/**"]

[[acceptance]]
text = "Given a C# repository, when frob ticket evidence add --provider dotnet runs with a TRX-producing command, then the TRX is parsed into evidence; the --provider value list is generated from the provider registry so a new provider is never missing"
bound = false
+++

Hullbreach game repro (B).
