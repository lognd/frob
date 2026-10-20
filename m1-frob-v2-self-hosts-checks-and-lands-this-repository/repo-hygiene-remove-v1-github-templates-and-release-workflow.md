+++
id = "01M3WYJ80T00Y0DN0YHTRYK0KK"
title = "Repo hygiene: remove v1 GitHub templates and release workflow, add .gitattributes"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0026"]
labels = ["milestone:2.0.0", "component:workspace"]
scope = [".github/**", ".gitattributes"]

[[acceptance]]
text = "Given a fresh clone, when a file is committed, then git prints no CRLF warning"
bound = true

[[acceptance]]
text = "Given .github, when read, then no template mentions Python, uv or pytest"
bound = true
+++

Follow-up from T-0003. Delete .github/workflows/release.yml (PyPI publish) and rewrite the issue and PR templates under .github for the Rust workspace (no uv run frob, no Python). Add .gitattributes with '* text=auto eol=lf' so commits stop printing CRLF warnings on this host, and normalize line endings in one commit. Also add Cargo.lock to [tickets] registry_files is already done; nothing else.
