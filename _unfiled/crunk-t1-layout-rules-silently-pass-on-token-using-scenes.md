+++
id = "01M7AV3827P32YDAGDXDVS8CWV"
title = "crunk T1 layout rules silently pass on token-using scenes"
type = "bug"
category = "todo"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:15:50Z"
updated = "2026-11-13T17:11:58Z"
labels = ["no-story"]
scope = ["crates/crunk-*/**"]

[[acceptance]]
text = "A token-using scene yields a finding or Unresolved, never a silent pass."
bound = false
+++

H2: LAYOUT001/002, RESP001, SLOP020-029 pass without evidence when tokens are used; report Unresolved instead. Source: frob-audit-grimble-crunk.md (Opus audit).
