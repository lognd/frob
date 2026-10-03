+++
id = "01M413T4PVDKZ014X3WB5DF7DD"
title = "release cut and release changelog work in consumer repositories"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-03T14:48:39Z"
updated = "2026-10-03T15:17:29Z"
scope = ["crates/frob-release/**", "crates/gob-config/**", "docs/design/releases.md", "frob.toml", "crates/frob/src/release_cmd.rs", "crates/frob/tests/cli.rs", "crates/frob/tests/release.rs", "crates/frob/tests/release_cut.rs", "crates/frob/tests/snapshots/cli__doctor_fresh_repo.snap", "crates/frob/tests/snapshots/cli__init_frob_toml.snap", "docs/reference/config.md", "docs/reference/rules/REL001.md", "docs/schemas/config.json"]

[[acceptance]]
text = "Given a repository with no [release] products, when release cut 0.1.0 runs, then exactly one tag v0.1.0 is created"
bound = true

[[acceptance]]
text = "Given [release] tag and products configured, when release cut runs, then one tag per product follows the pattern"
bound = true

[[acceptance]]
text = "Given a hand-written CHANGELOG.md with an Unreleased heading, when release changelog runs, then it inserts the generated section without refusing and leaves the hand-written text intact"
bound = true
+++

Reported by the cloc repository (FROB_FEEDBACK item 13): release cut tags every entry of SHIPPED_BINARIES (frob-vX, grimble-vX) and release changelog hard-codes a '### frob' product heading and refuses an existing hand-written CHANGELOG.md without an integrity marker. Make products and the tag pattern configuration ([release] tag = "v{version}", products = [...]; frob's own repo sets frob and grimble), default to one product named after the repository with tag v{version}, omit the product heading when there is one product, and adopt an existing CHANGELOG.md (insert above the first version heading, keep what is above, mark only the generated section).
