+++
id = "01M4D95REZP3PP4F2WD7ASNXV3"
title = "PAIR001 React vocabulary: useEffect that starts fetch, timers, listeners or subscriptions without a returned cleanup or abort"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M2Y1SS0MVHB8M891RN134SE7"
reporter = "lognd"
created = "2026-10-08T08:13:16Z"
updated = "2026-10-08T08:13:16Z"
scope = ["changelog.d/**", "crates/gob-ir/**", "crates/gob-frameworks/**"]

[[acceptance]]
text = "Given useEffect with setInterval and no returned clearInterval, when checked, then PAIR001 fires"
bound = false

[[acceptance]]
text = "Given a returned cleanup that clears the interval, when checked, then clean"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md row W03 (4.2 N21); notes/research/creators-web-2026-10-08.md WADV013 (6 voices: Abramov, React docs, Remix, Solid, Svelte, Vue) and 5.2 item 1 (no ESLint rule exists). Depends on the re-scoped ~4CESXMT.
