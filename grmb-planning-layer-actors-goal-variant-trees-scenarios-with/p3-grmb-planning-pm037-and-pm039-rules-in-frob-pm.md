+++
id = "01M6BYKR4XHDEJVRDYN5952RXW"
title = "P3 grmb planning: PM037 and PM039 rules in frob-pm"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4FDBDC401KMNN4C12QTA3PK"
reporter = "lognd"
created = "2026-11-01T16:20:49Z"
updated = "2026-11-05T19:27:55Z"
labels = ["grimble", "no-story"]
scope = ["crates/frob-pm/src/rules/**", "crates/frob-pm/tests/**", "docs/design/pm-enforcement.md", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M6BYKR12BCNQ3P3BR3J3AR58"

[[acceptance]]
text = "Given an obligation with no implementing ticket, when frob check runs, then PM037 is reported on that anchor at Error severity (Advisory is retired); PM038 rule id and message are defined for the close guard"
bound = true
+++

Child of ~2QTA3PK. Rules PM037, PM038 definition and PM039. Doubt: PM038 and PM039 semantics are in grmb-planning.md 10 / pm-enforcement.md; implementer must read them. Work no-story.
