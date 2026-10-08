+++
id = "01M4CXRXWTA9DG9DTV5R149H7C"
title = "VIS rules: perceptual diff thresholds and design-versus-build comparison"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXRV40WWJQKHWJJBKJT1HZ"
reporter = "lognd"
created = "2026-10-08T04:54:01Z"
updated = "2026-10-08T04:54:01Z"
scope = ["changelog.d/**", "crates/crunk-check/**", "crates/crunk-gallery/**"]

[[acceptance]]
text = "Given a rendered build that differs from its design scene beyond threshold, when checked at T2, then VIS fires with the diff image path"
bound = false
+++

docs/design/crunk.md section 6.
