+++
id = "01M336K770YH3HCTRJ6P1MZAEK"
title = "FMT001 directive-wrap Tier-A pass rewrites directive-shaped lines inside string literals (lexical scan, not token-based)"
type = "bug"
category = "triage"
priority = "high"
points = 2
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:00Z"
aliases = ["T-5344"]
labels = ["milestone:0.534.0", "v1-cluster:G1"]
scope = ["src/frob/gates/_fmt_directives.py", "tests/test_gates_fmt_directives.py"]
+++

Observed on T-5108's first land (2026-09-22): the pre-land FMT001 directive-wrap pass reflowed '# frob:...' continuation lines that lived INSIDE a triple-quoted test fixture string in tests/test_narrative_migrate.py, corrupting the fixture and failing two evidence tests. The wrap must decide from parsed tokens (a comment token, not a physical line starting with '#'), per the owner rule that checks and fixes are token/grammar-based, never lexical. Positive control: a test file whose string literal contains a long '# frob:tests ...' line must be left byte-for-byte untouched by the wrap, while a real comment line of the same text is wrapped.
