+++
id = "01M5H3RXWHYH6MRJX6B2M35H0F"
title = "crunk rename: support design/tokens custom tokens and derived scale tokens"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T06:11:32Z"
updated = "2026-10-22T20:45:18Z"
scope = ["crates/crunk/src/rename.rs", "crates/crunk/tests/rename.rs"]

[[acceptance]]
text = "Given a custom token in design/tokens, when crunk rename runs, then the definition and all references are rewritten"
bound = false

[[acceptance]]
text = "Given a derived scale or font token, when crunk rename runs, then it is renamed or refused with a specific coded reason"
bound = false
+++

Found while working ~PAN1YXT: rename covers [palette] colors and [layers] only; Custom tokens and derived scale/font tokens refuse with E-RENAME-KIND.
