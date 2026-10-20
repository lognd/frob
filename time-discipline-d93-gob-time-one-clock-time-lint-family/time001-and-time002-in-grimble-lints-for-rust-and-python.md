+++
id = "01M44R5W4WJEXFM000S8KVQQN5"
title = "TIME001 and TIME002 in grimble-lints for Rust and Python"
type = "story"
category = "todo"
priority = "medium"
parent = "01M44R5D47XBH3E2N3B8FNMT9F"
reporter = "lognd"
created = "2026-10-05T00:42:18Z"
updated = "2026-10-05T00:42:31Z"

[[links]]
kind = "blocked-by"
target = "01M41RV691XZQ5W2EW821PHK3V"

[[acceptance]]
text = "Given a Python datetime.now() without tz whose value is stored, when grimble checks it, then TIME001 fires; and a value only displayed stays quiet"
bound = false

[[acceptance]]
text = "Given a naive datetime compared with an aware one, when grimble checks it, then TIME002 fires"
bound = false
+++

rules.md 3.2 (D93): TIME001 local-clock-read and TIME002 naive-aware-mix in grimble-lints for Rust and Python first (the two first-party adapters), as GRL rules in the standard pack where they need def-use, following how PATH001-003 were built (rules.md 3.1, ~21PHK3V). Callee vocabulary per language for current-time reads, local-zone constructors and naive/aware datetime construction; a language without those roles reports Unresolved, never clean. Fixtures that fire and stay quiet for each rule and language; explain pages; [time] knobs in grimble.toml if needed; this repository raises TIME001 and TIME002 to Error in its own config.
