+++
id = "01M4HW9GZT9T70NGGAHAH1CKJF"
title = "ticket evidence add --provider file accepts a gitignored or untracked path, leaving evidence that exists on no ref"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-10T03:04:20Z"
updated = "2026-10-24T00:18:47Z"
labels = ["adoption:logand-app"]
scope = ["crates/frob-evidence/src/**", "changelog.d/**", "crates/frob-evidence/tests/file_committed.rs"]

[[acceptance]]
text = "Given a file evidence ref that is gitignored or untracked, when evidence add runs, then it is refused with a remedy (commit the file, or use command evidence); a tracked file is accepted"
bound = true
+++

logand.app-v2 F-577 (.frob/*.json).
