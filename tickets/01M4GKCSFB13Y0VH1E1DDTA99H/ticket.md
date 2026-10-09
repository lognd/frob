+++
id = "01M4GKCSFB13Y0VH1E1DDTA99H"
title = "Generated report directories (coverage HTML, playwright-report, htmlcov) are walked by crunk and frob rules; exclude them by default"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T15:09:35Z"
updated = "2026-10-09T15:09:35Z"
labels = ["adoption:logand-app"]
scope = ["crates/gob-walk/**", "crates/gob-config/**", "crates/crunk-check/**", "changelog.d/**"]

[[acceptance]]
text = "Given a vitest HTML coverage report at the repository root, when frob check runs, then crunk and frob rules skip it by default (a documented default exclude list), and config can opt back in"
bound = false
+++

logand.app-v2 F-555: 122 COLOR001 findings blocked land.
