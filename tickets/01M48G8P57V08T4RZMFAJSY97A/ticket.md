+++
id = "01M48G8P57V08T4RZMFAJSY97A"
title = "cargo dev ci shear fails on experimental: unused insta dev-dependency in gob-frameworks"
type = "bug"
category = "in-progress"
priority = "high"
reporter = "lognd"
created = "2026-10-06T11:40:56Z"
updated = "2026-10-06T12:01:33Z"
scope = ["crates/gob-frameworks/Cargo.toml", "Cargo.lock"]

[[acceptance]]
text = "cargo dev ci --step shear passes on experimental"
bound = true
+++

gob-frameworks (~AVXTRHX) landed after the shear step (~19X37CZ) with an unused insta dev-dependency in crates/gob-frameworks/Cargo.toml, so cargo dev ci --step shear fails on experimental (measured on goway 2026-10-06). Remove it; land does not run cargo dev ci, so the agent brief now requires a full remote cargo dev ci before reporting.
