+++
id = "01M3ZX7KAV3E0A5EZN2E40P4QY"
title = "External packs: fetch by URL and tree digest, vendor, hardened extraction"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:25Z"
updated = "2026-10-03T03:34:25Z"
idempotency_key = "m2-packs-external"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-packs/src/external/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7K7BN0CEADJFMCTGEA64"

[[acceptance]]
text = "Given an archive with a symlink entry or a path escaping the root, when fetched, then extraction is refused with PACK005 before anything is written"
bound = false

[[acceptance]]
text = "Given a digest mismatch, when fetched, then nothing is vendored and the error names both digests"
bound = false
+++

Implements plugins.md section 2; security.md section 2.8.

HTTPS only, redirects only within the declared host, tree digest verified before extraction, absolute, .. , symlink, hardlink and device entries refused, size and file-count caps; vendored then treated as a repository pack, shown as ext:HOST/NAME.
