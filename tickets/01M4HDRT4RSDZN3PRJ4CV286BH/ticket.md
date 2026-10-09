+++
id = "01M4HDRT4RSDZN3PRJ4CV286BH"
title = "Ticket check still spends 17 s in repo:obligations and 20-57 s in sibling:grimble; scope or skip them for diff-unrelated tickets"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T22:50:32Z"
updated = "2026-10-09T22:51:49Z"
scope = ["crates/frob-check/src/sibling/mod.rs", "frob.toml", "changelog.d/**"]

[[acceptance]]
text = "Given a ticket whose diff touches no grimble inputs, when check --ticket runs, then sibling:grimble is skipped and reported not evaluated"
bound = false

[[acceptance]]
text = "Given frob.toml, when this lands, then cargo-deny, cargo-shear, typos, zizmor and actionlint declare inputs (Cargo.lock/Cargo.toml/deny.toml; **/Cargo.toml; text files for typos; .github/workflows/** for zizmor and actionlint) so a ticket touching none of them skips them at land (inputs key from ~RDRSZC5)"
bound = false
+++

found while working ~040TA9M: after skipping PM groups, check --ticket (profiling build, load 47) still shows repo:obligations 17.3 s, sibling:grimble 21.0 s, tool:cargo-deny 17.4 s, tool:cargo 18.1 s.
