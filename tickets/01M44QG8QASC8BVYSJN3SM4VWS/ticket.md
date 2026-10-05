+++
id = "01M44QG8QASC8BVYSJN3SM4VWS"
title = "release section dates use the local zone while every other frob date is UTC"
type = "bug"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-05T00:30:30Z"
updated = "2026-10-05T00:30:30Z"

[[acceptance]]
text = "Given a release cut at 00:06 UTC while the local zone is on the previous day, when the changelog section is dated, then the date follows the documented zone rule"
bound = false
+++

crates/frob/src/release_cmd.rs (around lines 113, 539 and 807) dates release sections with jiff::Zoned::now().date(), the machine's local zone, while ~AAZFNR5 made frob-pm's Day::today() the UTC day and documented UTC as the zone for dates (docs/design/pm-enforcement.md section 4). A release cut around midnight gets a different date depending on the machine, and two machines can disagree. Use the same UTC day helper (or decide and document an explicit release-date zone in releases.md) so every date frob writes follows one rule, and add a boundary test.
