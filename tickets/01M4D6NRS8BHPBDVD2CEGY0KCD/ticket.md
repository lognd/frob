+++
id = "01M4D6NRS8BHPBDVD2CEGY0KCD"
title = "One key order for materialized [pm] knobs across frob.toml, the init snapshot and the config sync list"
type = "chore"
category = "done"
outcome = "done"
priority = "low"
points = 1
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T07:29:34Z"
updated = "2026-10-11T23:32:56Z"
scope = ["changelog.d/**", "crates/frob/**", "crates/gob-config/**", "frob.toml"]

[[acceptance]]
text = "Given a new knob, when added through the derive, then the three outputs agree with one order"
bound = true
+++

Follow-up from ~57FX1J2: each new knob needs three hand-placed edits.
