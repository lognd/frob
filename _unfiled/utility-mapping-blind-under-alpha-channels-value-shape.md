+++
id = "01M1T07J3DM50YB583KQ92G87C"
title = "utility mapping blind under alpha_channels value shape"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:02Z"
aliases = ["crunk:T-0109"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/query/engine.py", "tests/unit/test_query.py", "tests/system/test_e2e_45_selfmap.py"]

[[acceptance]]
text = "given namespace_keys and alpha_channels both on, when explain and unused run against a TSX using text-<token>/40, then the site and utility list and BOTH the -rgb var and its parent count as used"
bound = false
+++

Finale demo catch: with alpha_channels the self-derived mapping values are rgb(var(--x-rgb) / <alpha-value>), which the utility map's ^var\(...\)$ extraction does not match -- resolution went blind exactly for the config the adopting shell runs. Fix: extract the FIRST var(--name) anywhere in the mapping value; a -rgb name also marks its parent token as used. Extend E2E-45 to run with both knobs on.
