+++
id = "01M48Q28JZ3AB6FNJ8H2Y6V4G2"
title = "Verb admission test: every registered verb has a justified cli.md row"
type = "task"
category = "todo"
priority = "medium"
parent = "01M48Q27GE8C1P6JS1CXKTCQ3S"
reporter = "lognd"
created = "2026-10-06T13:39:49Z"
updated = "2026-10-06T13:39:49Z"
scope = ["crates/gob-cli/**", "crates/gob-dev/**", "docs/design/cli.md"]

[[acceptance]]
text = "a registered verb without a row fails naming it"
bound = false

[[acceptance]]
text = "a row without a registered verb fails naming it"
bound = false

[[acceptance]]
text = "the justification column exists for every row"
bound = false
+++

D104 enforcement: a test walks the gob-cli verb registry of frob, grimble and crunk and fails when a verb (hidden aliases excluded) has no row in docs/design/cli.md section 4 naming its justification (effect, policy or object), or when a row names a verb that is not registered, so the implementation and the design cannot drift again (board was top-level in code while the design had removed board-as-separate).
