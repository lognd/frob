+++
id = "01M68Y86KWQ2XHRY924QVTP23M"
title = "grimble-model conformance_corpus fails: severities differ (error vs warn/advisory), 14 cases"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T12:16:47Z"
updated = "2026-10-31T18:54:31Z"
scope = ["crates/grimble-model/**"]

[[acceptance]]
text = "conformance_corpus passes"
bound = false
+++

found while working ~TBXYWWK: fails on experimental independent of that change; MDL008/MDL005/MDL017/MDL019 emitted as error where corpus expects warn/advisory.
