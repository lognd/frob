+++
id = "01M5CQERZ8JATBXZ3KBDPWJ77V"
title = "Measured corpus counts actions uses/needs refs as F2 evidence"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-20T13:19:18Z"
updated = "2026-11-11T00:55:02Z"
scope = ["crates/gob-symbols/tests/it/measured.rs", "crates/gob-symbols/src/**", "changelog.d/**"]

[[acceptance]]
text = "measure() counts file.refs so the actions adapter measures F2 and the PINNED entry is removed"
bound = false
+++

found while working ~89M8282: the github-actions adapter declares F2 (RefSite refs) but measure() sees no ref in the term/scopes, so it is pinned F2 vs F1 in measured.rs PINNED. Teach measure() to count file.refs, then drop the pin.
