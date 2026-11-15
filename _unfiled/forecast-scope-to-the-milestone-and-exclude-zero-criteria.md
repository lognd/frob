+++
id = "01M7EXQW83NZMQPXGEPHRBV6G6"
title = "forecast: scope to the milestone and exclude zero-criteria closes"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:19:01Z"
updated = "2026-11-15T06:19:01Z"
labels = ["no-story"]

[[acceptance]]
text = "Forecast ignores closes outside the milestone (test)"
bound = false

[[acceptance]]
text = "Zero-criteria closes are excluded (test)"
bound = false
+++

Source: frob-audit-meta.md M9. Evidence: crates/frob-metrics/src/forecast.rs uses all closes. Remedy: filter by milestone and drop zero-criteria closes. Files: forecast.rs.
