+++
id = "01M5V7400HHPFFVXFJFD52N2C4"
title = "Scoped capability grants (may ... at) are ignored"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-26T04:22:25Z"
updated = "2026-10-26T04:22:25Z"
scope = ["crates/grimble-capabilities/**"]

[[acceptance]]
text = "a may ... at grant only grants cells inside its selector, with a test"
bound = false
+++

Found while working ~FKKYQ41. Scoped grants (may ATOM at SELECTOR) are ignored when computing granted cells; they should only grant within the selected symbols.
