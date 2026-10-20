+++
id = "01M413T4GRZDC843XFPG31XEZ3"
title = "Evidence capture writes non-ASCII tool output into ledger event files"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-03T14:48:39Z"
updated = "2026-10-03T15:18:54Z"
scope = ["crates/frob-evidence/**"]

[[acceptance]]
text = "Given a provider whose output contains non-ASCII characters, when evidence is recorded, then every byte written under tickets/ is ASCII and the escaped text round-trips on show"
bound = true

[[acceptance]]
text = "Given nextest evidence, when recorded, then the provider was run with plain non-Unicode output"
bound = true
+++

Reported by the cloc repository (FROB_FEEDBACK item 10): ticket evidence add --provider nextest stores nextest's summary, including U+2500 box-drawing characters, in tickets/<id>/events/*.toml. Ledger files must be ASCII (owner rule; consumer CI gates grep for non-ASCII). Run providers with plain output (NEXTEST_HIDE_PROGRESS_BAR, no Unicode) and escape any remaining non-ASCII as \\u{XXXX} when writing captured text, consistent with the text-origin escaping of D82 (see ~61CRGKF).
