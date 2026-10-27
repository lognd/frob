+++
id = "01M1QDTV247TC4H7F9V0GA24DP"
title = "TW001 message prefixes bypass spec.naming; dynamic getattr on scales"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:35Z"
aliases = ["crunk:T-0068"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/rules/_tailwind.py", "tests/unit/test_rules_tailwind.py"]

[[acceptance]]
text = "given an empty color-adjacent prefix config, when TW001 names neighboring steps, then the var names come from spec.naming; and the scales lookup is statically resolved (OPAQUE gate clean)"
bound = false
+++

Post-land quarantine caught OPAQUE001 (getattr(spec.scales, scale_attr) with a table-driven name); review of the site found the worse sibling: _LENGTH_PREFIXES hardcodes '--space'/'--radius'/'--font-size' message prefixes, so a configured [tokens.prefixes] would make TW001 messages name tokens that do not exist. Replace the table with static accessors + the spec.naming token builders (space_token/radius_token/font_size_token).

## Drop reason
- 2026-09-05: duplicate of auto-filed T-0067, which holds the _tailwind.py lease; fix lands under T-0067 with the same acceptance (spec.naming message tokens + static scales access)
