+++
id = "01M557T34HJ8C5QEKJQZRMWG8B"
title = "crunk-tailwind publish = false is blocked: crunk-tokens depends on it (left out of ~6995F8R)"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-17T15:31:11Z"
updated = "2026-10-17T15:31:11Z"
+++

~6995F8R set publish = false on five of six crates; crunk-tailwind is a normal dependency of the published crunk-tokens, so it cannot be unpublished without deciding crunk-tokens first. Decide: keep crunk-tailwind published, or make crunk-tokens a dev/optional consumer.
