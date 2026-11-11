+++
id = "01M75P1TKHGFXY6GTM5W90QNYF"
title = "Make install-linker action retry apt on mirror outages"
type = "bug"
category = "todo"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-11-11T16:11:28Z"
updated = "2026-11-11T16:11:31Z"
scope = [".github/actions/install-linker/action.yml", "changelog.d/**"]

[[acceptance]]
text = "install-linker retries apt-get update and install up to 5 times with backoff"
bound = false
+++
