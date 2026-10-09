+++
id = "01M4H0RE1Q9A1M47ZT7Q1ZG43K"
title = "DOC rule: resolve prose citations of the form 'x.md section N' and 'x.md#anchor' in docs, crates and notes; a citation to a missing file, section or anchor is a finding"
type = "story"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T19:03:08Z"
updated = "2026-10-09T19:03:08Z"
labels = ["docs"]
scope = ["crates/frob-obligations/**", "crates/gob-text/**", "changelog.d/**"]

[[acceptance]]
text = "Given a crate comment or doc citing 'tickets.md section 6' where tickets.md has no section 6, when frob check runs, then a finding names the citation and the target; citations resolved through docs/MOVED.toml after consolidation are followed, not reported"
bound = false
+++

Owner 2026-10-09: why didn't we catch the doc drift? The docs consolidation audit (notes/review/docs-consolidation-2026-10-09.md) found 427 plain-text section citations that nothing resolves, several dangling.
