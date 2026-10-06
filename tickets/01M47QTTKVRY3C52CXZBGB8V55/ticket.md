+++
id = "01M47QTTKVRY3C52CXZBGB8V55"
title = "Rule coverage test: every registered rule has an mdtest fire/clean pair or a fixture"
type = "story"
category = "in-progress"
priority = "high"
points = 5
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:33:59Z"
updated = "2026-10-06T06:59:07Z"
scope = ["crates/gob-mdtest/**", "crates/gob-rules/**", "crates/frob-check/tests/**", "crates/grimble-check/tests/**", "crates/crunk-check/tests/**", "crates/frob-check/Cargo.toml", "crates/grimble-check/Cargo.toml", "crates/crunk-check/Cargo.toml"]

[[acceptance]]
text = "the test runs for frob, grimble and crunk registries"
bound = false

[[acceptance]]
text = "removing a rule's only corpus makes it fail naming the rule"
bound = false

[[acceptance]]
text = "the allowlist has a ticket handle per entry"
bound = false
+++

build-test-ci.md section 6, ruff's per-rule fixtures. A registry-driven test per product iterates every registered rule id and fails naming each rule with neither an mdtest fire and clean pair nor a fixture under resources/test/fixtures/FAMILY/RULE.ext with a diagnostics snapshot. Existing gaps are listed in one allowlist file with a ticket per gap, which may only shrink.
