+++
id = "01M4D959JV48VTTKYTEKRWYGNW"
title = "VIS001: item visibility wider than its uses (Advisory), binding rustc unreachable_pub where present"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-08T08:13:00Z"
updated = "2026-10-08T08:13:00Z"
scope = ["changelog.d/**", "crates/grimble-arch/**"]

[[acceptance]]
text = "Given a pub item whose references_to hi set lies inside its own package, when checked, then VIS001 fires; given an Unknown edge from outside, then Unresolved"
bound = false

[[acceptance]]
text = "Given an item re-exported from the crate root, when checked, then clean"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md row K33 (4.2 N13): notes/research/mining-report-2026-10-08.md C19 0.5 percent; ManySStuBs4J CHANGE_MODIFIER 7.8 percent of one-statement Java fixes (notes/research/mining-report-2026-10-08.md 6.4); notes/research/creators-systems-2026-10-08.md ADV023, ADV020.
