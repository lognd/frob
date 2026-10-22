+++
id = "01M4CXRDTCFVJ4VPZKAJ22BXS0"
title = "Scene dialect: restricted HTML and CSS with data-id and component tags; SCENE001 for unsupported properties"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4CXRC0Z94MGD87PY9NH8B7X"
reporter = "lognd"
created = "2026-10-08T04:53:44Z"
updated = "2026-10-22T05:51:18Z"
scope = ["changelog.d/**", "crates/crunk-scene/**", "crates/gob-symbols/**", "docs/design/crunk.md"]

[[acceptance]]
text = "Given a scene using an unsupported CSS property, when checked, then SCENE001 fires naming it"
bound = false
+++

docs/design/crunk.md section 3; parsing through the gob HTML/CSS adapters.
