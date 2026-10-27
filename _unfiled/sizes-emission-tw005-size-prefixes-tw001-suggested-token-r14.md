+++
id = "01M1T07J3W8WRN917QCFXFCZZB"
title = "Sizes emission + TW005 size prefixes + TW001 suggested_token (r14, A-066)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:41Z"
aliases = ["crunk:T-0124"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/tokens/render.py", "src/crunk/tokens/io.py", "src/crunk/rules/_tailwind.py", "tests/unit/test_tokens.py", "tests/unit/test_rules_tailwind.py", "tests/system/test_e2e_51_sizes.py", "src/crunk/query/engine.py"]

[[acceptance]]
text = "given a declared sizes scale, when tokens regenerate, then tokens.css carries size entries and the theme maps all six sizing categories so a namespaced min-h utility resolves in explain"
bound = false

[[acceptance]]
text = "given h-9 w-9 min-h-9 h-full and min-h-[111px] against a declared 112, when checked, then three TW005 fire, h-full passes, and the TW001 names the 112 token as suggested_token"
bound = false
+++

Implement the r14 design: size tokens exported after radii, the six sizing theme categories mapping to size vars with the spacing default-key table for the collision warning, TW005 extended to the five size prefixes with numeric-key-only judgment, TW001 off-scale lengths carrying suggested_token. Single ticket per the r14 build order.
