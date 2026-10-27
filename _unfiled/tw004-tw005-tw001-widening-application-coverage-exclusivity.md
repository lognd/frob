+++
id = "01M1T07J3RRV1GK1RPT0R4KYQZ"
title = "TW004/TW005 + TW001 widening: application-coverage exclusivity (r13, A-063)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:40Z"
aliases = ["crunk:T-0120"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/rules/_tailwind.py", "src/crunk/tokens/tw_defaults.py", "src/crunk/spec/models.py", "tests/unit/test_rules_tailwind.py", "tests/unit/test_tokens.py", "tests/system/test_e2e_49_50_exclusivity.py", "src/crunk/rules/engine.py"]

[[acceptance]]
text = "given a TSX className bg-black/10 with a declared palette, when checked, then TW004 fires with a suggested token and bg-transparent passes"
bound = false

[[acceptance]]
text = "given declared layers and a 0/4/8/16 spacing scale, when z-10, -z-[5], p-5, max-h-[32dvh], and max-w-[900px] are checked, then TW005, TW001, TW005, TW001 fire respectively and max-w passes"
bound = false
+++

Implement the r13 design landed in CR-24, the application-coverage section of 02-specification, rules.md, and tokens.md: default color names table in the tw-defaults data module, TW004 default-color denylist, TW005 default-scale-key bypass, TW001 widened to zIndex arbitraries, size prefixes, and non-px-comparable units in governed families. Single ticket per the r13 build order.
