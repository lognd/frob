+++
id = "01M4CTTXC1E5MQEDFMY5JDQ45M"
title = "Real --text views for the everyday verbs (ticket show/list/doable, check, doctor, cycle show/list, work, land)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:40Z"
updated = "2026-10-08T04:02:40Z"
scope = ["changelog.d/**", "crates/frob/**", "crates/gob-cli/**", "crates/frob-*/src/render*"]

[[acceptance]]
text = "Given each listed verb, when run with --text, then the output is a human view with snapshot tests, not the envelope's key tree"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md MEDIUM: --text is a dump of the JSON envelope except for board.
