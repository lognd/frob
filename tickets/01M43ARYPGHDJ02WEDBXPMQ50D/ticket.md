+++
id = "01M43ARYPGHDJ02WEDBXPMQ50D"
title = "crunk-adapters: FrameworkAdapter trait, react_ts and react_router discovery"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:49Z"
updated = "2026-10-06T04:32:50Z"
idempotency_key = "crunk-plan-adap"
labels = ["area:crunk"]
scope = ["crates/crunk-adapters/**", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M43ARX764095Q4VWABWXXV5H"

[[links]]
kind = "blocked-by"
target = "01M43ARXMH7RJ63G8096KKJF80"

[[acceptance]]
text = "Given a Vite React Router project, when discovery runs, then routes equal the Python list"
bound = false

[[acceptance]]
text = "Given a project with no registered framework, when discovery runs, then the result is an explicit NotApplicable, not an empty success"
bound = false

[[acceptance]]
text = "Given the trait, when a second adapter is registered in a test, then it is selected by detection"
bound = false
+++

Port adapters/ (960 LOC): trait, registry, react_ts (project detection moves onto the trait: v1 T-0226) and react_router route discovery; non-hard-target frameworks stay deferred (v1 T-0166, T-0159). Port tests/unit/test_adapters*.py.
