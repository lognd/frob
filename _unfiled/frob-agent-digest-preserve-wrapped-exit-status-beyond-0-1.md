+++
id = "01M6R3FQGA0ZRECRXNW3EBWYDQ"
title = "frob agent digest: preserve wrapped exit status beyond 0/1"
type = "bug"
category = "in-progress"
priority = "low"
points = 1
reporter = "lognd"
created = "2026-11-06T09:36:53Z"
updated = "2026-11-06T10:15:57Z"
labels = ["no-story"]
scope = ["crates/gob-dev/profile.toml"]

[[acceptance]]
text = "Digest help and docs state that the wrapped exit status is only in data.exit_code and that frob exits 0-4; summary text prints the wrapped status."
bound = false
+++

frob exits only 0-4, so digest reports the wrapped command's status only in data.exit_code; decide whether to map or document. Found by ~MRH4QCR. Also fix ~MRH4QCR scope glob crates/frob-cli/** -> crates/frob/**.
