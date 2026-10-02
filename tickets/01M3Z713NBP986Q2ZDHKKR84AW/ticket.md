+++
id = "01M3Z713NBP986Q2ZDHKKR84AW"
title = "G06: gob-check pipeline crate; exceptions into gob-rules; polarity and subjects_examined"
type = "task"
category = "todo"
priority = "high"
points = 13
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:24Z"
updated = "2026-10-02T21:06:24Z"
idempotency_key = "m2-gobcheck"
labels = ["milestone:2"]
scope = ["crates/gob-check/**", "crates/gob-rules/**", "crates/gob-macros/**", "crates/frob-check/**", "crates/frob-obligations/**", "docs/reference/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z712AFAG3GCEAZ66KPBWD1"

[[links]]
kind = "blocked-by"
target = "01M3Z712DPZN71ZQDS6PXY6QQV"

[[acceptance]]
text = "Given frob check before and after the extraction on this repository, when both run, then findings are identical and the new crate has no frob dependency"
bound = false
+++

grimble-model.md 9.7 and rules.md: extract the product-neutral pipeline (walk, inputs, per-file and repo rules, caches, exception application, render) from frob-check into gob-check; exception matching into gob-rules; Rule derive gains polarity and must_measure, Finding gains subjects_examined and the required mark; frob-check becomes frob's driver; generated rule pages show polarity.
