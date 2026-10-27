+++
id = "01M1QDTV33B10GWVPYSRB7TPS1"
title = "R10-B: SIZE001 (CR-22)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:38Z"
aliases = ["crunk:T-0099"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/rules/_scales.py", "src/crunk/rules/engine.py", "tests/unit/test_rules_scales.py", "tests/system/test_e2e_41_sizes.py", "src/crunk/spec/naming.py"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV322Y6MS3KDRTTCYT3G"

[[acceptance]]
text = "given width 45px against sizes [16,24,32,44,64], when check and fix run, then SIZE001 warns naming neighbors with a suggested token and fix snaps 45 to 44 in CSS but never in TSX; max-width is exempt; spacing fallback holds when sizes is undeclared (E2E-41)"
bound = false
+++

Per r10 rules.md: SIZE001 in _scales.py reusing _off_scale and the SPACE001 fix/suggested-token machinery over width/height/min-width/min-height/max-height; max-width exempt; sizes falls back to spacing; register in engine.
