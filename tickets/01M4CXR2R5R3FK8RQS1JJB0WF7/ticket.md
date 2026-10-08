+++
id = "01M4CXR2R5R3FK8RQS1JJB0WF7"
title = "Colour-blind safe and dark modes: every COLOR and CONTRAST rule runs once per declared mode"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-08T04:53:33Z"
updated = "2026-10-08T04:53:33Z"
scope = ["changelog.d/**", "crates/crunk-check/**", "crates/crunk-spec/**"]

[[acceptance]]
text = "Given a contrast failure only in the cb-safe mode, when crunk check runs, then the finding names the mode"
bound = false
+++

docs/design/crunk.md section 7.
