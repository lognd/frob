+++
id = "01M4CXQXGBYXFCDTSQQVQKN1E9"
title = "Token dialect compiles to DTCG 2025.10: tiers, aliases, composites, scopes and modes through the resolver module"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-08T04:53:28Z"
updated = "2026-10-08T04:53:28Z"
scope = ["changelog.d/**", "crates/crunk-spec/**", "crates/crunk-tokens/**", "crates/crunk/**"]

[[acceptance]]
text = "Given design/tokens TOML with aliases, composites and two modes, when compiled, then the DTCG output validates against the DTCG schema and resolves every alias per mode"
bound = false

[[acceptance]]
text = "Given an existing crunk.toml palette, when compiled, then it yields the same tokens as before"
bound = false
+++

docs/design/crunk.md section 2 (D109). Existing crunk.toml [palette]/[scales] stay valid as a view.
