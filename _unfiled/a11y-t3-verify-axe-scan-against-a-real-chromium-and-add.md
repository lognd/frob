+++
id = "01M5HBZP01JBP86ZXKPMP4BYVK"
title = "A11Y T3: verify axe scan against a real Chromium and add keyboard focus replay"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T08:35:02Z"
updated = "2026-10-28T12:55:56Z"
labels = ["no-story"]
scope = ["crates/crunk-gallery/**"]

[[acceptance]]
text = "Given Playwright, axe-core and Chromium installed, when PlaywrightAxe scans a page with a known violation, then the finding carries the axe rule id and node"
bound = false

[[acceptance]]
text = "Given a screen, when T3 replays Tab through it, then focus order and focus visibility are asserted"
bound = false
+++

Found while working ~PT56WSN. The axe runner was only tested with recorded axe JSON and a fake node; node/render.mjs axe mode was never run against real Playwright, axe-core and Chromium. Keyboard focus replay (design doc section 4, T3) was not done.

no-story: internal engineering task in crunk-gallery; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
