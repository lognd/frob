+++
id = "01M4FCB4D3R6YE9F538E6RW233"
title = "frob migrate v1 converts frob.toml: map v1 keys ([tickets] default_milestone, [testing], [profile]) to v2 or report each dropped key with its reason"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 3
parent = "01M4CTTVCB8JJ9JB2NQHQP5ARY"
reporter = "lognd"
created = "2026-10-09T03:47:06Z"
updated = "2026-10-09T16:28:33Z"
labels = ["adoption:hullbreach"]
scope = ["crates/gob-dev/**", "crates/gob-config/**", "docs/guides/upgrade-from-v1.md", "changelog.d/**"]

[[acceptance]]
text = "Given a v1 frob.toml with default_milestone, [testing] and [profile], when the conversion runs, then the v2 frob.toml loads without refusal and every unmapped v1 key is listed with its reason; the key mapping table is in docs/guides/upgrade-from-v1.md"
bound = false
+++

Hullbreach adoption: v2 refuses v1 keys. Document the mapping and convert; folds into frob migrate v1 (~HQP5ARY).
