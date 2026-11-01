+++
id = "01M6C3VFQJDG6CZV7VNZP5KR2Q"
title = "grimble-model: report MDL012 for title items and load notes/research/grmb-corpus mockups"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M69AHE03R04HDKKDT03B2YRN"
reporter = "lognd"
created = "2026-11-01T17:52:25Z"
updated = "2026-11-01T17:52:25Z"
scope = ["crates/grimble-model/src/parse/plan.rs", "crates/grimble-model/tests/corpus/**"]

[[links]]
kind = "blocked-by"
target = "01M6BYK3M8ZM6K3P9V3M7Y61ZQ"

[[links]]
kind = "blocked-by"
target = "01M6BYKA5HDJT3KSKGQ2QQ6V9H"

[[acceptance]]
text = "notes/research/grmb-corpus mockups d01..d11 and stress files load with only their documented findings"
bound = false

[[acceptance]]
text = "a title item reports MDL012 per grmb-spec 11.1"
bound = false

[[acceptance]]
text = "plan/web_app respelled from include-as to use"
bound = false
+++

found while working ~A1W814E: all mockups parse DAMAGED today (parser predates cycle 1 grammar); title is parsed silently; D157 membership rule not re-verified in plan_check.rs.
