+++
id = "01M5ETSE6D7CPPAVBD4KEM6AX5"
title = "GRL per-file bucket/component attribute for crunk ORG001/003/004/005"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-21T08:56:03Z"
updated = "2026-10-21T08:56:03Z"
+++

Split from ~CZSG7YJ. Expose a css_root-relative per-file bucket and component attribute (see bucket_for in crates/crunk-ingest/src/walk.rs) so rules can express ORG001, ORG003, ORG004, ORG005.
