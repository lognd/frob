+++
id = "01M4D94PD6M68GJ6MEDBVDP7MK"
title = "Public API checkers mapped to VERSION001: cargo-semver-checks, PublicApiAnalyzers, api-extractor, griffe"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4D8X558Q07HCMEBP224NQP4"
reporter = "lognd"
created = "2026-10-08T08:12:41Z"
updated = "2026-10-08T08:12:41Z"
scope = ["changelog.d/**", "crates/gob-check/**", "crates/frob-obligations/**"]

[[acceptance]]
text = "Given a removed public function and an unchanged version, when frob check --base runs the semver stage, then VERSION001 is an Error naming the item"
bound = false

[[acceptance]]
text = "Given a major version bump, when checked, then no finding"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md row K32 (4.2 N08): notes/research/mining-report-2026-10-08.md C35 breaking API, 67 percent blocking; notes/research/creators-systems-2026-10-08.md ADV012 (Hyrum's law), ADV023 public surface.
