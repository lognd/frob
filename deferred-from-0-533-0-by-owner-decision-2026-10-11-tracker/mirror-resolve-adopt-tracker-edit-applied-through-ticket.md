+++
id = "01M3ZX84XDSS3740Q6S5MQY4H6"
title = "mirror resolve --adopt: tracker edit applied through ticket verbs"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:43Z"
updated = "2026-10-03T03:39:11Z"
idempotency_key = "m2-mirror-resolve-adopt"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob/src/mirror_cmd.rs", "crates/frob-mirror/src/adopt.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7YW7S3BJ72FPRQ85F72V"

[[links]]
kind = "blocked-by"
target = "01M3ZX7Z0EM0DCAHC59PJH50MJ"

[[links]]
kind = "blocked-by"
target = "01M3ZX84SFSR050P2XV293C4MC"

[[acceptance]]
text = "Given a non-TTY stdin, when `--adopt` runs, then it exits 3 and changes nothing"
bound = false

[[acceptance]]
text = "Given a tracker edit to the scope section, when adopted, then it is refused because scope is repository-owned"
bound = false
+++

Implements mirror.md section 3.1; security.md section 2.11.

Needs a TTY, shows the diff with escaping, refuses edits by unmapped identities, can never change repository-owned fields (scope, acceptance, evidence, links); tracker text carries origin tracker and a length cap.
