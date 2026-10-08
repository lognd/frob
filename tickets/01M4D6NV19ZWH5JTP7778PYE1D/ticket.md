+++
id = "01M4D6NV19ZWH5JTP7778PYE1D"
title = "gob-ir: per-stratum poison records the affected nodes so checks taint only subjects that read them"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T07:29:37Z"
updated = "2026-10-08T07:29:37Z"
scope = ["changelog.d/**", "crates/gob-ir/**"]

[[acceptance]]
text = "Given a stratum with one poisoned node, when a check reads an unrelated subject, then that subject's verdict is definite"
bound = false
+++

Follow-up from ~NZMJSTK.
