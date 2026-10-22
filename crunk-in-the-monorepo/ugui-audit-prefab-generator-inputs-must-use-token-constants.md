+++
id = "01M4CXSD8DEYB69E5J7Q1ABGXK"
title = "uGUI audit: prefab generator inputs must use token constants; read-only prefab YAML literal audit"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4CXSAG0YPF18FX3KAPVX45C"
reporter = "lognd"
created = "2026-10-08T04:54:16Z"
updated = "2026-10-22T13:20:24Z"
scope = ["changelog.d/**", "crates/crunk-check/**", "crates/gob-mdtest/coverage-allowlist.toml"]

[[acceptance]]
text = "Given a generator with a Color literal, when checked, then the finding asks for the generated token constant"
bound = true
+++

docs/design/crunk.md section 7 (hullbreach HudPrefabBuilder.cs).
