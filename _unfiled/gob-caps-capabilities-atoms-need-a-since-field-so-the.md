+++
id = "01M5WAN9NAK2Z228S550D6FW61"
title = "gob-caps capabilities (atoms) need a since field so the changelog lists newly live atoms"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-26T14:43:32Z"
updated = "2026-10-26T14:43:32Z"
scope = ["crates/gob-caps/**", "crates/frob-release/**"]

[[acceptance]]
text = "A capability atom carries a since version, and frob release changelog lists atoms newly live in the release alongside rules"
bound = false
+++

Follow-up of VGQ66DC acceptance 2: only rules are covered today.
