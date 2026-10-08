+++
id = "01M4D95Q9WWPDZH86CMBMAZEDQ"
title = "TYPING004: network or file data cast to a declared type without validation (Advisory)"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T08:13:14Z"
updated = "2026-10-08T08:13:14Z"
scope = ["changelog.d/**", "crates/grimble-lints/**", "crates/gob-ir/**"]

[[acceptance]]
text = "Given await res.json() as User with no parse call on the value, when checked, then TYPING004 fires"
bound = false

[[acceptance]]
text = "Given schema.parse(await res.json()), when checked, then clean"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md row W07 (4.2 N15); notes/research/creators-web-2026-10-08.md 5.2 item 10 (Zod docs, Pocock: res.json() as T at the boundary).
