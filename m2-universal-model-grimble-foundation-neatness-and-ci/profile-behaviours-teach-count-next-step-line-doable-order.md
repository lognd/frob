+++
id = "01M3ZX87VKDKC0N65NH77EBEJP"
title = "Profile behaviours: teach count, next-step line, doable order, failure help"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:46Z"
updated = "2026-10-14T21:04:37Z"
idempotency_key = "m2-nav-profile-behaviour"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob/src/profile.rs", "crates/gob-cli/src/render.rs", "crates/gob-cli/src/cli.rs", "crates/frob/src/product.rs", "crates/frob/src/lib.rs", "crates/frob/src/ticket/read.rs", "crates/frob/src/profile_cmd.rs", "docs/design/navigation.md", "docs/reference/cli/frob.md", "changelog.d/01M3ZX87VKDKC0N65NH77EBEJP.*", "crates/gob-cli/src/lib.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX87FNRDNXXC2VTYPHN173"

[[links]]
kind = "blocked-by"
target = "01M3ZX87QPD21PCSSSAJHVK7HJ"

[[acceptance]]
text = "Given the newcomer profile, when `frob work ~X` succeeds, then the output ends with `next: ...`; under experienced it does not"
bound = true

[[acceptance]]
text = "Given both profiles on the same repository, when check runs, then findings and exit code are identical"
bound = true
+++

Implements navigation.md section 4.1 (table).

Newcomer: teach always for the first five occurrences of each rule then first, a one-line next step after each verb, good-first first in doable, three likely commands and the guide page on failure; experienced: first, none, priority order, did-you-mean only. Never changes what a check decides.
