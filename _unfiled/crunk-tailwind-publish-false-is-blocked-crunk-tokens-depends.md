+++
id = "01M557T34HJ8C5QEKJQZRMWG8B"
title = "crunk-tailwind publish = false is blocked: crunk-tokens depends on it (left out of ~6995F8R)"
type = "task"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-17T15:31:11Z"
updated = "2026-11-04T15:06:39Z"
labels = ["good-first", "no-story"]
scope = ["crates/crunk-tailwind/Cargo.toml"]

[[acceptance]]
text = "Given crunk-tokens depends on crunk-tailwind, when the publish decision is applied, then cargo publish --dry-run succeeds for crunk-tokens"
bound = false
+++

~6995F8R set publish = false on five of six crates; crunk-tailwind is a normal dependency of the published crunk-tokens. Decide: keep crunk-tailwind published, or make crunk-tokens a dev/optional consumer.

## Start here

Read both Cargo.toml files and the publish settings in ~6995F8R.
