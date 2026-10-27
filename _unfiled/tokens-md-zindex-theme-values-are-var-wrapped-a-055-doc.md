+++
id = "01M1T07J3K5TG7TZ8GKGWDE0YF"
title = "tokens.md: zIndex theme values are var-wrapped (A-055 doc truth-up)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:40Z"
aliases = ["crunk:T-0115"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["docs/design/subsystems/tokens.md"]

[[acceptance]]
text = "given tokens.md, when read, then the zIndex sentence describes var(--layer-name) values"
bound = true
+++

T-0114 changed the emission; the Tailwind theme rendering sentence still describes bare integers. One-sentence truth-up; the in-code AFFECT waivers pointing at T-0024 for this can then be retired by natural WAIVE004 aging.
