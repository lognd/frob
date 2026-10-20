+++
id = "01M4D958QKMX7VHFJMRMAWDT22"
title = "DUP R1-R3 in grimble-arch: exact and alpha-renamed token clones above min_tokens with three or more occurrences (Advisory)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-08T08:12:59Z"
updated = "2026-10-08T08:12:59Z"
scope = ["changelog.d/**", "crates/grimble-arch/**"]

[[acceptance]]
text = "Given three copies of a 60-token block across two languages, when grimble check runs, then one DUP finding lists all sites"
bound = false

[[acceptance]]
text = "Given two copies, when checked at the default min_occurrences, then no finding"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md row K16 (4.2 N12): notes/research/mining-report-2026-10-08.md C03 2.2 percent, R-DUPLICATION 7.9 percent of genuine refactors; notes/research/creators-systems-2026-10-08.md ADV018 (10.5 weighted voices); the threshold is contested (notes/research/creators-systems-2026-10-08.md ADV120, notes/research/creators-web-2026-10-08.md WADV087), hence min_occurrences = 3 and Advisory.
