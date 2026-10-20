+++
id = "01M43ATBDWVSJBXP7TEQ6DBW3W"
title = "Rules SPACE001, TYPE001-003, RADIUS001, SIZE001 (Rust, tier-0)"
type = "story"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:29:35Z"
updated = "2026-10-09T05:52:02Z"
idempotency_key = "crunk-plan-rscale"
labels = ["area:crunk", "creates:crates/crunk-rules/src/rules/space001*", "creates:crates/crunk-rules/src/rules/type00*", "creates:crates/crunk-rules/src/rules/radius001*", "creates:crates/crunk-rules/src/rules/size001*"]
scope = ["crates/crunk-rules/src/scales/**", "crates/crunk-rules/src/typography/**", "crates/crunk-rules/tests/scales*.rs", "crates/crunk-rules/tests/typography*.rs", "crates/crunk-rules/src/rules/space001*", "crates/crunk-rules/src/rules/type00*", "crates/crunk-rules/src/rules/radius001*", "crates/crunk-rules/src/rules/size001*", "crates/crunk-rules/src/rules/mod.rs", "crates/crunk-rules/src/lib.rs", "crates/crunk-rules/tests/rules.rs", "crates/crunk-rules/tests/support/mod.rs", "docs/crunk/rules/README.md"]

[[links]]
kind = "blocked-by"
target = "01M43ARVJKKN4EXCQF1NRTJ3KW"

[[links]]
kind = "blocked-by"
target = "01M43ATASM383KB9130JY79XVV"

[[acceptance]]
text = "Given `margin: 13px` and a 4px-based scale, when checked, then SPACE001 fires with the nearest step"
bound = true

[[acceptance]]
text = "Given `max-width: 640px`, when checked, then SIZE001 does not fire"
bound = true

[[acceptance]]
text = "Given a font-family outside the declared stacks, when checked, then TYPE002 fires"
bound = true
+++

Port rules/_scales.py and _typography.py: margin, padding, gap, inset off the spacing scale; font-size off scale; family stack; weight; border-radius; width and height (max-width exempt). Shared scale-match helper with rem/px conversion and fix_tolerance; fixes attached for SPACE001, TYPE001, RADIUS001, SIZE001. Rust for the same reason as the color ticket (unit conversion and tolerance). Port tests/unit/test_rules_scales.py, test_rules_typography.py, e2e 03, 11.
