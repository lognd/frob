+++
id = "01M6AJ9384JTFTS1CABZ0TG0KQ"
title = "grimble-bind owner.rs: build one UnitIndex per file instead of per unit (quadratic)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T03:26:02Z"
updated = "2026-11-01T05:38:09Z"
labels = ["creates:crates/grimble-bind/src/owner.rs"]
scope = ["crates/grimble-bind/src/owner.rs"]

[[acceptance]]
text = "A count-based test proves owner resolution builds one index per file"
bound = true
+++

owner.rs:265 calls owner_of_unit per unit, rebuilding the index each time; use UnitIndex + owner_of_unit_in. Found by the 12CQ663 implementer.
