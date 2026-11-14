+++
id = "01M5H5P5R4J2XAE0QABN6MVYC8"
title = "crunk: per-locale content key completeness rule"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T06:44:59Z"
updated = "2026-11-14T14:27:36Z"
scope = ["crates/crunk-rules/**"]

[[acceptance]]
text = "CONTENT007 fires once per content key that one locale defines and another locale lacks, and passes when all locales define the same keys"
bound = true
+++

found while working ~VAAWD0R: keys missing from non-default locale files are unchecked.
