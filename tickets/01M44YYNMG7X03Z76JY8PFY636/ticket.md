+++
id = "01M44YYNMG7X03Z76JY8PFY636"
title = "frob migrate config: v1 frob.toml to v2 frob.toml and grimble.toml"
type = "story"
category = "todo"
priority = "high"
parent = "01M44YYN4E7SXWHQB3H7EHD37P"
reporter = "lognd"
created = "2026-10-05T02:40:42Z"
updated = "2026-10-05T02:42:58Z"

[[acceptance]]
text = "Given a v1 frob.toml with known, severity and unknown keys, when frob migrate config runs, then the v2 files hold the mapped keys and every unknown key is reported"
bound = false

[[acceptance]]
text = "Given the dry run, when it runs, then nothing is written"
bound = false
+++

migration.md section 1 row frob.toml: known keys mapped and split into frob.toml and grimble.toml by family (boundaries.md), [gates.severity] collapsed to the rows that differ from v2 defaults, profile mapped per rules.md section 7, unknown keys reported, never dropped silently. Dry run by default, --apply writes.
