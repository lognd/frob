+++
id = "01M4D95TNEY7MCTS3A4F9HC26C"
title = "Client route change without document.title update or focus move or announcement (crunk-web A11Y, Advisory)"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M2Y1SS0MVHB8M891RN134SE7"
reporter = "lognd"
created = "2026-10-08T08:13:18Z"
updated = "2026-10-08T08:13:18Z"
scope = ["changelog.d/**", "crates/crunk-check/**", "crates/gob-frameworks/**"]

[[acceptance]]
text = "Given routes that render without setting the title or moving focus, when crunk check runs, then one finding per route"
bound = false

[[acceptance]]
text = "Given a route-level title and focus handler, when checked, then clean"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md row W05 (4.2 N23); notes/research/creators-web-2026-10-08.md WADV045, WADV058 (Sutton, O'Hara, Pickering, de Vries, W3C) and 5.3 (hullbreach applies).
