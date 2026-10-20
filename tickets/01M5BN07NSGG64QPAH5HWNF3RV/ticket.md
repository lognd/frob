+++
id = "01M5BN07NSGG64QPAH5HWNF3RV"
title = "frob agent: preserve settings.json key order on write"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-20T03:17:10Z"
updated = "2026-10-20T03:17:10Z"
+++

serde_json without preserve_order alphabetizes keys when the claude emitter rewrites settings.json. Found while working ~VHZ1FDQ.
