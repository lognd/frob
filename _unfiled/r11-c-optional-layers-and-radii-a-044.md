+++
id = "01M1QDTV3BW2J5AFYFKEF0BDBZ"
title = "R11-C: optional layers and radii (A-044)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:39Z"
aliases = ["crunk:T-0107"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/spec/models.py", "src/crunk/spec/load.py", "src/crunk/tokens/render.py", "src/crunk/rules/_scales.py", "src/crunk/rules/_layers.py", "tests/unit/test_spec.py", "tests/unit/test_tokens.py", "tests/unit/test_rules_scales.py", "tests/system/test_e2e_47_optional_dims.py"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV33B10GWVPYSRB7TPS1"

[[acceptance]]
text = "given a spec with no layers section and radii = [], when tokens and check run, then no layer/radius tokens are emitted, LAYER001/RADIUS001 stay silent, and everything else works (E2E-47)"
bound = false
+++

Per r11 spec.md/tokens.md/rules.md: layers optional (absent -> {}), radii accepts empty (validator min_length 0, ascending when non-empty); render/entries/token_names skip empty dimensions; RADIUS001 (and SIZE001's radii-adjacent paths if any) guard the empty scale; LAYER001 already iterates spec.layers so absent = silent -- prove it. spacing/font_sizes stay required.
