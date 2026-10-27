+++
id = "01M1T07J3JHEK671H165RXH10S"
title = "zIndex theme values emit var(--layer-x) like every other category (A-055)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:40Z"
aliases = ["crunk:T-0114"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/tokens/render.py", "tests/unit/test_tokens.py", "tests/unit/test_query.py", "tests/system/test_e2e_45_selfmap.py"]

[[acceptance]]
text = "given a TSX using z-<layer> utilities, when explain and check --report run, then the layer token lists its site and utility and leaves unused_tokens; the emitted zIndex theme values are var-wrapped"
bound = false
+++

Field finding A-055 with a source-level diagnosis from the adopting session: zIndex entries in render_tailwind/theme_mapping are bare integer literals, unlike color/spacing/fontSize/borderRadius which are var()-wrapped, so utility_token_map's var()-search can never link z-<name> to --layer-<name> -- structurally unused/blind. Fix per their option 1: emit var(--layer-<name>) (consistent with every category; also makes tokens.css the live z source). theme_mapping stays in lockstep by construction (one home). Goldens updated; extend the selfmap E2E with a z-<layer> utility asserting explain sites + unused exclusion.
