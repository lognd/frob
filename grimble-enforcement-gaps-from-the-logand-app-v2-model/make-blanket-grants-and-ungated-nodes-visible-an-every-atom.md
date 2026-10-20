+++
id = "01M4GYBZZB9Z4QPMW451DC0JFG"
title = "Make blanket grants and ungated nodes visible: an every-atom grant over a whole tree is reported as a declared trust zone, and nodes that are not CAP subjects (no code-owning selector) are listed as ungated"
type = "story"
category = "todo"
priority = "medium"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T18:21:23Z"
updated = "2026-10-09T18:21:23Z"
labels = ["grimble", "adoption:logand-app"]
scope = ["crates/grimble*/**", "changelog.d/**"]

[[acceptance]]
text = "Given a node granting every atom at a broad glob (tests/**, scripts/**) and nodes with no code-owning selector, when grimble status runs, then the report lists the trust zones and the ungated nodes explicitly with counts, so coverage is never mistaken for enforcement"
bound = false
+++

logand model: 32 of 57 grant lines are blanket tooling grants over scripts/tests/.github/ops; only 8 of 27 nodes are CAP subjects. Argument-scoped atoms (net.connect:HOST, grimble-model.md section 2) should be the recommended form for network grants.
