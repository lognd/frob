+++
id = "01M68Y86KWQ2XHRY924QVTP23M"
title = "grimble-model conformance_corpus fails: severities differ (error vs warn/advisory), 14 cases"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T12:16:47Z"
updated = "2026-10-31T19:18:32Z"
scope = ["crates/grimble-model/**", "docs/design/grimble-model.md", "docs/reference/rules/MDL008.md"]

[[acceptance]]
text = "conformance_corpus passes"
bound = true
+++

found while working ~TBXYWWK: fails on experimental independent of that change; MDL008/MDL005/MDL017/MDL019 emitted as error where corpus expects warn/advisory.
