+++
id = "01M1QDTV1F4JDK0Z6X8JBS63PB"
title = "var() refs nested in function values are invisible to ingest"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0047"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/ingest/parse.py", "tests/unit/test_ingest.py", "docs/design/subsystems/ingest.md"]

[[acceptance]]
text = "given a declaration value color-mix(in srgb, var(--color-accent) 50.2%, transparent), when it is ingested, then var_refs contains --color-accent with a correct span"
bound = false
+++

Found by the r4 live demo: crunk fix now writes color-mix(in srgb, var(--color-accent) 50.2%, transparent), but _extract_value_facts only inspects top-level tokens, so the var() inside color-mix is not a LocatedVarRef -- query uses misses it and COLOR002 cannot judge nested refs. Recurse into function-token arguments when scanning for var() refs (colors/lengths stay top-level: a nested literal is the function's business).
