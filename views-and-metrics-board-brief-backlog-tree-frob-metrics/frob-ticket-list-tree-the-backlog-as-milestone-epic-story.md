+++
id = "01M48Q2A6GSSETPGKGJ6NJDNWV"
title = "frob ticket list --tree: the backlog as milestone, epic, story, task with roll-ups"
type = "story"
category = "done"
outcome = "done"
priority = "high"
parent = "01M48Q294B33TB7C0GSATZRGJB"
reporter = "lognd"
created = "2026-10-06T13:39:51Z"
updated = "2026-10-13T08:20:22Z"
scope = ["crates/frob-ledger/**", "crates/frob/src/ticket/**", "crates/frob/tests/**", "typos.toml"]

[[acceptance]]
text = "a fixture ledger renders the expected tree (snapshot) with roll-up points and percent done"
bound = true

[[acceptance]]
text = "orphans appear under Unparented"
bound = true

[[acceptance]]
text = "JSON carries the same tree"
bound = true
+++

The backlog view (D104: a flag, not a verb): a hierarchy by parent links (milestone, epic, story, task), rank order within a level, points and roll-up points with percent done per node, blocked and doable markers, folding below a depth (--depth N, like clocx --rows), filters shared with ticket list. Orphans are listed under an Unparented node, never dropped.
