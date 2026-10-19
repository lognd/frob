+++
id = "01M5ACKBFC59N3JC3HQBTC5F6V"
title = "Five mdtest corpus cases expect=fire but the rule returns Unresolved (READ001, SIB001, CLAIM003, MDL021, COLOR002)"
type = "bug"
category = "todo"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-19T15:31:05Z"
updated = "2026-10-19T15:31:16Z"

[[acceptance]]
text = "mdtest corpus tests for frob-check, grimble-model, grimble-check and crunk-rules pass under strict mode"
bound = false
+++

Found by 1X6M6MS strict mode. Cases in frob-check, grimble-model, grimble-check, crunk-rules fail with 'expected at least one X finding that is not Unresolved'. Fix the rule or the corpus block.
