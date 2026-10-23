+++
id = "01M1QDTV1J94YKR28YG47V7ABQ"
title = "ORG005 message uses root-relative paths; document query-never-fails (A-013, A-015)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0050"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/rules/_org.py", "tests/unit/test_rules_org.py", "tests/system/test_e2e_12_ungoverned.py", "docs/commands/query.md", "frob.lock"]

[[acceptance]]
text = "given an ungoverned file, when check runs, then the ORG005 message text carries spec-root-relative paths for both the file and css_root"
bound = false
+++

Per r5 rules.md: org005 relativizes the message's file and css_root paths against spec.root (the violation path column is already relative via the shell). docs/commands/query.md gains an explicit exit-codes note: query never exits 1; violations filtering is a view, check is the gate.
