+++
id = "01M4CXV0A8THFSQZGY22SM2G7J"
title = "grl-spec.md 7.0: denotational semantics of GRL into K3 over lo/hi structures (count as intervals, within N truncation as Unknown, polarity map, static NotApplicable, defs as views)"
type = "docs"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T04:55:09Z"
updated = "2026-10-09T04:16:40Z"
scope = ["changelog.d/**", "docs/design/grl-spec.md", "docs/design/README.md"]

[[acceptance]]
text = "Given the semantics, when the ten example rules are evaluated by hand, then each verdict follows compositionally and COV001 never fires on a truncated reach"
bound = true
+++

notes/review/formal-review-2026-10-08.md section 4 item 3; fixes the polarity table (2.3), the within bug and NotApplicable as a fourth value.
