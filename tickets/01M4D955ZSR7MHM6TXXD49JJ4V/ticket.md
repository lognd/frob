+++
id = "01M4D955ZSR7MHM6TXXD49JJ4V"
title = "PAIR001 Unity vocabulary: += in OnEnable without -= on teardown, RegisterCallback, action Enable/Disable, Addressables Load/Release"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-08T08:12:51Z"
updated = "2026-10-08T08:12:51Z"
scope = ["changelog.d/**", "crates/gob-ir/**"]

[[acceptance]]
text = "Given event += in OnEnable and no -= on any teardown root, when checked, then PAIR001 fires naming both sites"
bound = false

[[acceptance]]
text = "Given a lambda subscription, when checked, then the result is Unresolved"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md row U05 (4.2 N20); notes/research/creators-games-2026-10-08.md GADV031 (lapsed listener: Nystrom, Hipple, Unity docs), GADV079. Depends on the re-scoped ~4CESXMT.
