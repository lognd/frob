+++
id = "01M68ZBT7WG74CE1RWERSBPWE6"
title = "P1 grmb planning: parser, AST and contextual recognition for the seven planning items"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-31T12:36:14Z"
updated = "2026-10-31T13:14:38Z"
scope = ["crates/grimble-model/src/{ast,parse}.rs", "crates/grimble-model/tests/**"]

[[links]]
kind = "blocked-by"
target = "01M4FDBAAEX7HMVM8H6VKN98M6"

[[acceptance]]
text = "grmb-planning section 12 and 13 worked examples parse with zero MDL Errors"
bound = false

[[acceptance]]
text = "a major-2 model naming a node system or page loads unchanged"
bound = false
+++

Split from ~VKN98M6 (lexer tokens and keyword table done there, commit 74289fdea2). Parse system actor goal step scenario impl page per grmb-planning 3, contextual at item position only, hole recovery, major-2 compat (node named system/page loads unchanged).
