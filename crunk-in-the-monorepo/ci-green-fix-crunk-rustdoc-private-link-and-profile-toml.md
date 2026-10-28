+++
id = "01M61KHST2XVE7GQCKQK33PC9M"
title = "CI green: fix crunk rustdoc private link and profile.toml scenarios for crunk export leaves"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-28T15:55:06Z"
updated = "2026-10-28T16:23:58Z"
scope = ["crates/crunk/**", "profile.toml", "crates/gob-dev/profile.toml"]

[[acceptance]]
text = "cargo doc link to private crate::tokens::preview in crunk export is fixed so the Docs CI job passes"
bound = true

[[acceptance]]
text = "every crunk export leaf command has a scenario or a skip reason in profile.toml so the profile CI job passes"
bound = true
+++

CI on experimental fails in Docs (rustdoc private link in crunk export) and profile (crunk export csharp/css/tailwind/uss lack scenarios). Run 40718326507.
