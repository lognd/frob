+++
id = "01M1QDTV39F4T4QTR520RQPNB5"
title = "R11-D: semantic drift for JSON artifacts (A-048)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:39Z"
aliases = ["crunk:T-0105"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/tokens/io.py", "tests/system/test_e2e_48_semantic_drift.py", "docs/commands/tokens.md", "tests/unit/test_tokens_drift.py"]

[[acceptance]]
text = "given a formatter-rewrapped generated JSON artifact, when tokens --check runs, then it passes; a value edit fails; tokens.css byte edits fail as before (E2E-48)"
bound = false
+++

Per r11 tokens.md (Semantic drift for JSON artifacts): the check path compares .json artifacts by parsed equality (unparseable counts as drifted); css stays byte-exact. Document in the command doc.
