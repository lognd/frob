+++
id = "01M4DPJN74DSB5XJZ8TJ6DA5EV"
title = "Dev channel: the ensure-prerelease step handles a draft dev release; pin the 403 cause on a throwaway ref"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T12:07:30Z"
updated = "2026-10-08T12:07:30Z"
scope = ["changelog.d/**", ".github/workflows/**"]

[[acceptance]]
text = "Given a draft dev release, when the dev job runs, then it is found and reused; the 403 cause is recorded in build-test-ci.md"
bound = false
+++

Follow-ups from ~1QDWWPS; the post-land run refuted the old-tag-diff hypothesis.
