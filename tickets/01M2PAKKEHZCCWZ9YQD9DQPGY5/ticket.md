+++
id = "01M2PAKKEHZCCWZ9YQD9DQPGY5"
title = "post-land sweep residue from T-4517: COV002 in src/frob/lang/_support.py and src/frob/testing/_collect_csharp.py (new public symbols lack frob:doc/frob:tests edges)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M2KR6WD1KXN9PGT16RCMBYFN"
reporter = "agent"
created = "2026-09-17T00:00:00Z"
updated = "2026-09-17T00:00:02Z"
aliases = ["T-4561"]
labels = ["milestone:0.533.0"]
scope = ["src/frob/lang/_support.py", "src/frob/testing/_collect_csharp.py", "docs/modules/testing.md", "tests/unit/test_collect_csharp.py"]

[[acceptance]]
text = "GIVEN the T-4517 symbols in _support.py and _collect_csharp.py WHEN frob check runs THEN COV002 reports 0 findings for both files"
bound = false
+++

Raised by the post-land sweep of bcd55a738 (T-4517). Quarantine findings COV002:src/frob/lang/_support.py and COV002:src/frob/testing/_collect_csharp.py are filed onto this ticket. frob:waive BUG002 reason="sweep residue: the defect is a missing coverage edge, not runtime behaviour; no repro test can fail at parent"
