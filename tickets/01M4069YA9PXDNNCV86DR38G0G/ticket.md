+++
id = "01M4069YA9PXDNNCV86DR38G0G"
title = "PyPI publish job: trusted publishing for frob, protected environment, release notes"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:59Z"
updated = "2026-10-03T06:12:59Z"
idempotency_key = "m2-rel-publish-pypi"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = [".github/workflows/release.yml"]

[[links]]
kind = "blocked-by"
target = "01M4069Y1YR0XCN4BKDDH63PV1"

[[acceptance]]
text = "Given smoke failed, when the workflow runs, then no publish job starts"
bound = false

[[acceptance]]
text = "Given the job definition, when inspected, then id-token write is granted to no other job"
bound = false
+++

Job upload-frob needs build, smoke, verify-ci and the crates publish; environment pypi with a required reviewer (owner step, documented), id-token: write only on that job, pypa/gh-action-pypi-publish pinned by SHA; GitHub release notes body is the compiled changelog section plus the 0.532.0 upgrade notice from the notes ticket.
