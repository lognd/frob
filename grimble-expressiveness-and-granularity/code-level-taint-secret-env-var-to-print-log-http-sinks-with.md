+++
id = "01M6QA50A5BK89J2G8SCZ4WBPR"
title = "Code-level taint: secret env var to print/log/HTTP sinks with declassify"
type = "task"
category = "todo"
priority = "medium"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-06T02:14:07Z"
updated = "2026-11-06T02:14:07Z"
scope = ["crates/grimble-bind/**"]
+++

Split from NBEC70D acceptance 2: a fixture where a secret env var flows into print/log/HTTP fires a taint finding; routing through a declared declassify symbol is clean. NBEC70D landed the never-claim slice (CLAIM004).
