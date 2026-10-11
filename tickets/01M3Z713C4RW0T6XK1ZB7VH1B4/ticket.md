+++
id = "01M3Z713C4RW0T6XK1ZB7VH1B4"
title = "Exceptions: evaluate until= and add EXC016 and EXC017"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:24Z"
updated = "2026-10-11T01:04:11Z"
idempotency_key = "m2-excuntil"
labels = ["milestone:2", "creates:changelog.d/*.md"]
scope = ["crates/frob-obligations/**", "crates/gob-rules/**", "crates/frob-check/src/snapshot.rs", "crates/frob-check/src/product.rs", "docs/design/exceptions.md", "docs/reference/rules/EXC0*.md", "docs/reference/rules/README.md", "changelog.d/*.md"]

[[acceptance]]
text = "Given a defer whose until date has passed, when check runs, then the deferred finding returns with an EXC finding naming the expiry"
bound = true

[[acceptance]]
text = "Given an accept covering an Unresolved finding, when check runs, then the Unresolved finding stands and EXC016 is raised at the accept; a defer of it stays suppressed"
bound = true

[[acceptance]]
text = "Given a native suppression of a tool-bound rule (zizmor ignore, allow or eslint-disable of an id_map id) with no frob accept or defer of the mapped rule at that site, when check runs, then EXC017 is raised; with the exception present it is clean"
bound = true

[[acceptance]]
text = "EXC014, EXC016 and EXC017 each have a rule page under docs/reference/rules, a fire and a clean mdtest case, and a changelog fragment"
bound = true

[[acceptance]]
text = "Given a defer whose until day is today or later, or a metric target, when check runs, then the finding stays suppressed and no EXC014 is raised"
bound = true
+++

exceptions.md after the consistency review: defer and hotfix until= dates and metric bounds are evaluated; EXC016 (accept on an Unresolved finding) and EXC017 (native tool suppression of a bound rule without a frob exception) are implemented with corpora.
