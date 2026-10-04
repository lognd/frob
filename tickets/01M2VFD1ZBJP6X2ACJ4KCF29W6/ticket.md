+++
id = "01M2VFD1ZBJP6X2ACJ4KCF29W6"
title = "frob-suggest: replace blanket FROB_SUGGEST_ACK with per-rule token, update docs"
type = "bug"
category = "triage"
priority = "high"
parent = "01M2VFD1ZDWWNTW1FFGKHCKTS3"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-09-19T00:00:00Z"
aliases = ["T-5099"]
labels = ["milestone:0.536.0", "v1-cluster:E1"]
scope = [".claude/hooks/*", "tests/test_hook_frob_suggest.py", "docs/guides/*"]

[[acceptance]]
text = "blanket FROB_SUGGEST_ACK=1 is replaced by a per-rule allow FROB_SUGGEST_ALLOW=<rule-id> that only suppresses that rule"
bound = false

[[acceptance]]
text = "paste-ready 'prefix it with FROB_SUGGEST_ACK=1 up front' wording is removed from every block message"
bound = false

[[acceptance]]
text = "a stale FROB_SUGGEST_ACK=1 prints a one-line notice and is ignored (not honored as a bypass)"
bound = false

[[acceptance]]
text = "repo-shipped docs describing the ack (agent playbook or equivalent) are updated in the same change"
bound = false
+++

Leaf 3 of T-5101. See scratchpad/HOOK-AUDIT.md section 3.2.
