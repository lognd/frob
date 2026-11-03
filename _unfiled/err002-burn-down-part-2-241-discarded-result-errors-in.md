+++
id = "01M6G5ET01X5Z1EJV28Y74FZPV"
title = "ERR002 burn-down part 2: 241 discarded-result errors in crates leased by ~B755NCR, then delete [rules.ERR002]"
type = "chore"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-03T07:37:25Z"
updated = "2026-11-03T09:27:47Z"
scope = ["crates/**", "frob.toml"]
+++

Part 1 (ticket ~ZA87WAH) fixed 19 crates by dropping let _ = on write!/writeln! and fs cleanup (now .ok()). Remaining by crate: gob-plan 70, gob-symbols 34, gob-diagnostics 29, gob-ir 23, gob-rules 16, grimble-bind 13, frob-land 12, frob 10, frob-release 7, gob-cli 7, crunk-check 4, frob-check 4, crunk-gallery 3, crunk-rules 3, gob-check 2, grimble-arch 2, frob-pm 1, gob-fs 1. Same mechanical rewrite (script paren-matches the macro call). Then delete [rules.ERR002] from frob.toml. Blocked on ~B755NCR lease.
