+++
id = "01M44R5VQ21TNKGEC31V8FWY2P"
title = "gob-time: Stamp, Day, Shown and one injected Clock; migrate every wall-clock read; clippy confinement"
type = "story"
category = "in-progress"
priority = "high"
parent = "01M44R5D47XBH3E2N3B8FNMT9F"
reporter = "lognd"
created = "2026-10-05T00:42:18Z"
updated = "2026-10-05T00:42:47Z"

[[acceptance]]
text = "Given the workspace, when clippy runs, then any wall-clock or local-zone read outside gob-time is an error"
bound = false

[[acceptance]]
text = "Given a command that writes two dates, when it runs across midnight UTC, then both dates come from one clock snapshot"
bound = false
+++

time.md sections 1-3 (D93). Create the leaf crate gob-time with Stamp (UTC instant, RFC 3339 Z; moved from where it lives today), Day (UTC calendar day; moved from frob-pm), Shown (render-only local display), the Clock trait (now() -> Stamp, today() derived from now), SystemClock and FixedClock. Thread one clock through the command context so each verb reads it once. Migrate every wall-clock read in the workspace to it (grep SystemTime::now, Timestamp::now, Zoned::now, Date::today, TimeZone::system), including the release section dates (~release-date ticket filed 2026-10-04, fold it in and close it as covered). Add clippy disallowed-methods entries confining those reads to gob-time, with the one allow carrying a reason. std::time::Instant stays allowed. Reserve-name note: gob-time is a new published crate; report it so the coordinator reserves it.
