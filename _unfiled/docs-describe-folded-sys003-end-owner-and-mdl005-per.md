+++
id = "01M5MRKJQ8JA1EBR70QJ3C9H73"
title = "Docs: describe folded SYS003 end-owner and MDL005 per-selector findings in binding.md and grmb-spec.md"
type = "chore"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-23T16:13:20Z"
updated = "2026-10-23T17:04:53Z"
scope = ["docs/design/binding.md", "docs/design/grmb-spec.md", "crates/grimble-check/tests/design_docs.rs"]

[[acceptance]]
text = "Given binding.md section 5, when read, then it states one clause reaching several wrong-owner units reports once with count, owners, sample of 3 and per-unit rows in check --json bindings"
bound = true

[[acceptance]]
text = "Given grmb-spec.md example, when read, then it states two MDL005 findings with one finding listing both clause sites"
bound = false
+++

Found while working AKKMHBY. binding.md section 5 (end-owner) should say one clause reaching several wrong-owner units reports once (count, owners, sample of 3, per-unit rows in check --json bindings). grmb-spec.md line ~1601 says three MDL005 warnings for the example; it is now two (crates/grimble-*/** is one finding listing both clause sites).
