+++
id = "01M6R3FQGA0ZRECRXNW3EBWYDQ"
title = "frob agent digest: preserve wrapped exit status beyond 0/1"
type = "bug"
category = "todo"
priority = "low"
points = 1
reporter = "lognd"
created = "2026-11-06T09:36:53Z"
updated = "2026-11-06T09:36:53Z"
labels = ["no-story"]
+++

frob exits only 0-4, so digest reports the wrapped command's status only in data.exit_code; decide whether to map or document. Found by ~MRH4QCR. Also fix ~MRH4QCR scope glob crates/frob-cli/** -> crates/frob/**.
