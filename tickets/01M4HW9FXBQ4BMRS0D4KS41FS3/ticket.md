+++
id = "01M4HW9FXBQ4BMRS0D4KS41FS3"
title = "A bare-directory scope entry (backend/tests) matches nothing; treat it as dir/** and warn when any scope entry matches zero files"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-10T03:04:19Z"
updated = "2026-10-10T03:04:19Z"
labels = ["adoption:logand-app"]
scope = ["crates/frob-lease/src/**", "crates/frob-obligations/src/**", "changelog.d/**"]

[[acceptance]]
text = "Given scope entry backend/tests naming a directory, when leases and SCOPE001 evaluate it, then it covers backend/tests/** and a scope entry matching zero files (and not declared creates:) warns at ticket update and frob work"
bound = false
+++

logand.app-v2 F-576.
