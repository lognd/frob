+++
id = "01M44R5W4WJEXFM000S8KVQQN5"
title = "TIME001 and TIME002 in grimble-lints for Rust and Python"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M44R5D47XBH3E2N3B8FNMT9F"
reporter = "lognd"
created = "2026-10-05T00:42:18Z"
updated = "2026-10-21T18:01:11Z"
scope = ["crates/grimble-lints/**", "crates/grimble-check/src/**", "crates/grimble/src/explain_cmd.rs", "docs/design/rules.md", "docs/reference/rules/**", "changelog.d/01M44R5W4WJEXFM000S8KVQQN5.added.md"]

[[links]]
kind = "blocked-by"
target = "01M41RV691XZQ5W2EW821PHK3V"

[[acceptance]]
text = "Given a Python datetime.now() without tz whose value is stored, when grimble checks it, then TIME001 fires; and a value only displayed stays quiet"
bound = true

[[acceptance]]
text = "Given a naive datetime compared with an aware one, when grimble checks it, then TIME002 fires"
bound = true

[[acceptance]]
text = "TIME001 fires for a Rust Local::now() read stored in a value and stays quiet for Utc::now() and SystemTime::now()"
bound = true

[[acceptance]]
text = "TIME001 and TIME002 resolve import aliases and the tz keyword, so datetime.now(tz) and time.time() stay quiet and an aliased utcnow() fires"
bound = true

[[acceptance]]
text = "A walk with TypeScript or C# files reports TIME001 and TIME002 Unresolved, and a walk with no Rust or Python file is not applicable"
bound = false

[[acceptance]]
text = "The TIME rules are registered in the grimble check pipeline with a repo:time group, host and explain pages"
bound = false
+++

rules.md 3.2 (D93): TIME001 local-clock-read and TIME002 naive-aware-mix in grimble-lints for Rust and Python first (the two first-party adapters), as GRL rules in the standard pack where they need def-use, following how PATH001-003 were built (rules.md 3.1, ~21PHK3V). Callee vocabulary per language for current-time reads, local-zone constructors and naive/aware datetime construction; a language without those roles reports Unresolved, never clean. Fixtures that fire and stay quiet for each rule and language; explain pages; [time] knobs in grimble.toml if needed; this repository raises TIME001 and TIME002 to Error in its own config.
