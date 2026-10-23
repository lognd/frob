+++
id = "01M5HM3WE0PDTYAJ31B2C2A8A0"
title = "CRAFT001-005,007,009,011,012 presence rules (focus-visible, states, moment, fonts, press feedback, elevation, copy keys, optical alignment, intent coverage)"
type = "task"
category = "in-progress"
priority = "medium"
points = 8
parent = "01M4CXT3N608HMB1A77VTT4YXX"
reporter = "lognd"
created = "2026-10-22T10:57:08Z"
updated = "2026-10-23T05:34:06Z"
scope = ["crates/crunk-rules/**", "docs/reference/rules/**", "crates/crunk-check/**", "Cargo.lock"]

[[acceptance]]
text = "each of CRAFT001 CRAFT002 CRAFT003 CRAFT004 CRAFT005 CRAFT007 CRAFT009 CRAFT011 CRAFT012 is declared and fires on a fixture that lacks the presence it checks"
bound = true

[[acceptance]]
text = "a fixture that has the presence stays quiet for every one of these rules"
bound = false

[[acceptance]]
text = "each rule has a docs page and a registry row"
bound = false
+++

found while working ~DTBY8Q0; cut from its scope
