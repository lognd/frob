+++
id = "01M7EX7YGAJDAC9AM7H3C8BAJB"
title = "hunk_presence: parse quoted and tab-suffixed paths and check the git show exit status"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:10:19Z"
updated = "2026-11-15T06:10:19Z"
labels = ["no-story"]

[[acceptance]]
text = "A diff with a path containing a space or non-ASCII char is parsed to the correct path (unit test)"
bound = false

[[acceptance]]
text = "A failing git show yields an error, not an empty dropped-hunk set (unit test)"
bound = false
+++

Source: frob-audit-core.md M1 (and frob-audit-meta.md M1). Evidence: crates/frob-land/src/hunk_presence.rs parse_added (lines ~36-54) misses quoted (core.quotepath) or tab-suffixed paths, and the git show exit (~117) is unchecked, so a failed show reads as no dropped hunks. Remedy: parse quoted/tab paths (use -z or unquote), return Err on nonzero git show. Files: crates/frob-land/src/hunk_presence.rs.
