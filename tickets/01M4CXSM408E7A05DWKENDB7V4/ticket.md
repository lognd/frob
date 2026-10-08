+++
id = "01M4CXSM408E7A05DWKENDB7V4"
title = "Human review lock: crunk.lock [[review]] entries over subject content digests, HUMAN001/002, crunk review and crunk ack (person only)"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-08T04:54:24Z"
updated = "2026-10-08T04:54:24Z"
scope = ["changelog.d/**", "crates/gob-lock/**", "crates/crunk/**", "crates/crunk-check/**", "crates/crunk-spec/**", "crates/frob-release/**", "crates/gob-rules/**", "docs/design/releases.md", "docs/design/rules.md"]

[[acceptance]]
text = "Given an acked screen, when a token it uses changes, then HUMAN001 fires (Advisory in check and CI) naming the screen and the token, and clears only after crunk ack records a new digest"
bound = false

[[acceptance]]
text = "Given a stale human review, when frob release status and release cut run (or crunk check --gate release), then it is a blocking readiness item and cut refuses without --override --reason"
bound = false

[[acceptance]]
text = "Given require_signed and an ack added in an unsigned commit or by a key not listed for a reviewer, when crunk check runs, then HUMAN001 fires"
bound = false

[[acceptance]]
text = "Given crunk ack without a terminal and without --non-interactive, when it runs, then it refuses"
bound = false
+++

docs/design/crunk.md section 4.1 (owner requirement 2026-10-08): a design change fails the human tier until a person inspects and acks it. Reuse gob-lock (D28) with a new entry kind; digest covers sources, resolved tokens per mode, fonts and the render digest; reviewers allow-list; non-interactive acks are marked; [review] require_signed checks the introducing commit's signature against gob-trust keys. Severity: Advisory in check/CI, Error only at the release gate through a general rule field release_severity and a new release status readiness item (also update docs/design/releases.md and rules.md).
