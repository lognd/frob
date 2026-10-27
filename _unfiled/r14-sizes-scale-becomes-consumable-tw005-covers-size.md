+++
id = "01M1T07J3V9MQEV0WM9P37ZR25"
title = "r14: sizes scale becomes consumable; TW005 covers size prefixes (A-066)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:41Z"
aliases = ["crunk:T-0123"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["docs/design/01-customer-requirements.md", "docs/design/02-specification.md", "docs/design/subsystems/tokens.md", "docs/design/subsystems/rules.md", "docs/design/05-components.md"]

[[acceptance]]
text = "given the five design docs, when read, then sizes emission, the TW005 extension, the suggested-token addition, and CT/E2E ids are stated"
bound = true
+++

The adopting project's T-0212 drain found the sizes scale is naming-only (no tokens.css entries, no theme categories, so a declared size has no legitimate consumption path) and that TW005 omits the five size prefixes TW001 already governs, letting bare h-9/w-14 bypass a declared sizes scale. r14: sizes emits size tokens and the six sizing theme categories; TW005 extends to w/h/min-w/min-h/max-h with the spacing fallback; TW001 off-scale messages gain a suggested token.
