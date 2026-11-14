+++
id = "01M5F3BZ0WB8P8DKSRGNDAWKEE"
title = "crunk-web WEBPERF-assets follow-up: image formats, render-blocking stylesheets and font-display (CSS)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-21T11:25:58Z"
updated = "2026-11-14T15:27:12Z"
scope = ["packs/crunk-web/**", "crates/crunk-check/**", "crates/gob-plan/**", "docs/design/shared/grl-spec.md", "docs/guides/crunk.md"]

[[acceptance]]
text = "WEBPERF108 flags an @font-face without font-display; the at_rule GRL kind is cataloged and its examples pass"
bound = true
+++

Follow-up to ~4JWTCCP: image format hints (modern formats, picture/source), render-blocking stylesheet links, and @font-face font-display in CSS; needs value-pattern and CSS node support in GRL.
