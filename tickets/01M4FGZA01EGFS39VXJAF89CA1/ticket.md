+++
id = "01M4FGZA01EGFS39VXJAF89CA1"
title = "Attributes: resolve idents and check selector strings in attr values"
type = "story"
category = "todo"
priority = "low"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:08:02Z"
updated = "2026-10-09T05:08:02Z"
idempotency_key = "logand-gaps-E1"
labels = ["adoption:logand-app", "grimble"]
scope = ["crates/grimble-model/**", "crates/grimble-check/**", "docs/design/grmb-spec.md", "changelog.d/**"]

[[acceptance]]
text = "Given attr issued_by = backnd with no such node, when grimble check runs, then MDL006"
bound = false

[[acceptance]]
text = "Given an attr list holding a glob that matches no file, when grimble check runs, then MDL005 as for a clause selector"
bound = false

[[acceptance]]
text = "Given an attr string that is plain text, when grimble check runs, then no finding"
bound = false
+++

Repro 18-attr-values-unchecked (~/projects/frob-v2-repros/logand-grimble-20261009/18-attr-values-unchecked): attr issued_by = backnd (typo) and a glob string in an attr list matching no file are silent, so ceilings parked in attrs lose MDL005/SYS004 checking. grmb-spec 4.1 is silent on resolution: state it in the same change.
