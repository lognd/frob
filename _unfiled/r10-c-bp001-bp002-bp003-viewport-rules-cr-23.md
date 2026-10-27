+++
id = "01M1QDTV34W6BE0FCNHDMRNTWA"
title = "R10-C: BP001/BP002/BP003 viewport rules (CR-23)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:38Z"
aliases = ["crunk:T-0100"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/rules/_breakpoints.py", "tests/unit/test_rules_breakpoints.py", "tests/system/test_e2e_42_43_44_viewport.py", "crunk-cli"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV322Y6MS3KDRTTCYT3G"

[[acceptance]]
text = "given declared breakpoints, when check runs the CT-42/43/44 shapes, then BP001 flags the undeclared 900px query, BP002 flags md:flex without a base while hidden md:flex passes, BP003 flags width 900px while max-width passes; all three silent with no breakpoints (E2E-42..44)"
bound = false
+++

Per r10 rules.md _breakpoints.py bullet: BP001 over Stylesheet.media_queries (bp and bp-0.02 accepted); BP002 over utilities grouped by (sheet, line) -- responsive variant (declared names or min-[...]) + base_required family match (prefix for -suffixed entries, exact otherwise) + no variant-free same-family utility in the group; BP003 over width/min-width declarations vs the smallest declared breakpoint. Registered in engine; silent when the mapping is empty.
