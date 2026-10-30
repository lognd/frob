+++
id = "01M66JP3KAF056MN4AF8AZ7DKD"
title = "Product BaselineHost so BASE001/BASE002 run in frob check, plus check --fix prune"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T14:16:11Z"
updated = "2026-10-30T14:16:11Z"
scope = ["crates/frob-check/**"]

[[acceptance]]
text = "BASE001 and BASE002 fire from frob check using the head file, base-tip file and ledger ticket liveness; check --fix prunes dead keys"
bound = false
+++

found while working QJPFKV3: baseline adopt/prune verbs and land prune exist, but no product host feeds the BASE rules.
