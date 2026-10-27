+++
id = "01M1QDTV12QAGJQ4CSNHM7PR6B"
title = "alpha-aware COLOR001: variants conform, fixes preserve alpha (CR-09, A-003)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:31Z"
aliases = ["crunk:T-0034"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/values/color.py", "src/crunk/values/__init__.py", "src/crunk/rules/_color.py", "tests/unit/test_values.py", "tests/unit/test_rules_color.py", "tests/system/test_e2e_10_alpha.py", "docs/design/subsystems/values.md", "docs/design/subsystems/rules.md"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV10V68Y2CNVD2A8NT1Q"

[[acceptance]]
text = "given border-color: #50494559 with #504945 an opaque palette color, when check runs, then no violation; and a NEAR-palette translucent literal fixes to color-mix preserving alpha, never the opaque token (E2E-10)"
bound = false
+++

Field bug: fix rewrote #282828b2 -> var(--color-bg-primary), silently dropping alpha and turning a glass footer opaque. Per r4 values.md (rgb_hex, is_opaque) and rules.md alpha semantics: exact-rgb translucent over an OPAQUE palette entry is conformant; near translucent gets color-mix(in srgb, var(<token>) <alpha>%, transparent) within tolerance; distances rgb-only; messages say alpha is preserved. UT-VAL-06, UT-RUL-ALPHA, E2E-10.
