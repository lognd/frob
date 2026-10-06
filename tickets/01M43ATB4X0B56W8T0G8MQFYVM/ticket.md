+++
id = "01M43ATB4X0B56W8T0G8MQFYVM"
title = "Rules COLOR001-002 and CONTRAST001 (Rust, tier-0)"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:29:34Z"
updated = "2026-10-06T13:56:22Z"
idempotency_key = "crunk-plan-rcol"
labels = ["area:crunk"]
scope = ["crates/crunk-rules/src/color/**", "crates/crunk-rules/src/contrast/**", "crates/crunk-rules/tests/color*.rs", "crates/crunk-rules/tests/contrast*.rs"]

[[links]]
kind = "blocked-by"
target = "01M43ARVJKKN4EXCQF1NRTJ3KW"

[[links]]
kind = "blocked-by"
target = "01M43ATASM383KB9130JY79XVV"

[[links]]
kind = "relates"
target = "01M48FXB2PXX2FBXFKCFWSQYH1"

[[acceptance]]
text = "Given a literal within color_tolerance of a palette color, when checked, then COLOR001 fires with the palette token as suggestion"
bound = false

[[acceptance]]
text = "Given var(--missing) and an unindexed generated sheet, when checked, then COLOR002 is Unresolved, not clean"
bound = false

[[acceptance]]
text = "Given a role pair with ratio 4.4 and floor 4.5, when checked, then CONTRAST001 fires with the measured ratio"
bound = false
+++

Port rules/_color.py and _contrast.py. COLOR001 off-palette literal (alpha-aware, nearest-palette suggestion with color_tolerance), COLOR002 undefined var(--x) (needs the complete custom-property definition set; unresolved when a definition source is not indexed, polarity P-), CONTRAST001 role pair below the WCAG floor (4.5 default or per-role floor). Rust because the rules need color distance and WCAG ratio operators, which GRL (grl-spec.md section 4: twenty constructs, + - * only) does not have. Fix payloads are attached here and applied by the autofix ticket. Port tests/unit/test_rules_color.py, test_rules_contrast.py, e2e 02, 08, 10.
