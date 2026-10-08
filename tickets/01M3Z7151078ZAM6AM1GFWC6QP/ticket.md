+++
id = "01M3Z7151078ZAM6AM1GFWC6QP"
title = "NEAT first ten rules in grimble-lints with the effects capability"
type = "task"
category = "todo"
priority = "high"
points = 13
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:25Z"
updated = "2026-10-08T08:14:20Z"
idempotency_key = "m2-neat"
labels = ["milestone:2"]
scope = ["crates/grimble-lints/**", "crates/gob-ir/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z71393N041MWHC3SF903MG"

[[links]]
kind = "blocked-by"
target = "01M3Z713NBP986Q2ZDHKKR84AW"

[[links]]
kind = "blocked-by"
target = "01M3Z713YNM5666B7YFEHPFVKD"

[[links]]
kind = "blocked-by"
target = "01M3ZX7E5VPTH8J16D5APQDEAP"

[[links]]
kind = "blocked-by"
target = "01M3ZX7F1SGDAFM6ZQ8BP7TEN3"

[[links]]
kind = "blocked-by"
target = "01M3ZX7FYE5D1N2SY01VNVVACK"

[[acceptance]]
text = "Given a unit marked frob:honest that calls a clock vocabulary symbol, when grimble check runs, then NEAT010 reports the claim contradicted"
bound = false

[[acceptance]]
text = "Given the ruff PR 29076 shape in a fixture (dispatcher with a nested condition), when grimble check runs, then NEAT031 fires and the fixed shape is clean"
bound = false
+++

neatness.md section 4: NEAT002, 003, 004, 007, 006, 012, 013, 010 with 011, 030, 031; effects(unit) as Bounds with the callee vocabulary from [neat.effects]; claims verified, contradicted or Unresolved; thresholds materialized under [neat]; corpora with fire and clean; bound-tool entries for NEAT001, 005, 009.
