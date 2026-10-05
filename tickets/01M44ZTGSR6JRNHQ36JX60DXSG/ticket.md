+++
id = "01M44ZTGSR6JRNHQ36JX60DXSG"
title = "release.yml: workflow_dispatch dry run that builds and smokes everything and publishes nothing"
type = "chore"
category = "in-progress"
priority = "high"
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-05T02:55:52Z"
updated = "2026-10-05T02:56:03Z"

[[acceptance]]
text = "Given release.yml, when a workflow_dispatch event runs it, then every publishing job is skipped and the tag input is empty"
bound = false
+++

Split from ~Y3S3WBF so the rc evidence can follow the landed workflow. release.yml gains workflow_dispatch; release, crates and pypi jobs are guarded to push events so a dispatch requests no environment; the tag check is skipped off a tag push; wheels and archives build and smoke on all five targets. Guide and releases.md document the dry run.
