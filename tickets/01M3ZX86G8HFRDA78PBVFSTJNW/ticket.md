+++
id = "01M3ZX86G8HFRDA78PBVFSTJNW"
title = "Guide and .gitattributes installed from templates, refreshed on version change"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:45Z"
updated = "2026-10-03T03:34:45Z"
idempotency_key = "m2-nav-guide-templates"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-ledger/src/gen/guide.rs", "crates/frob-ledger/templates/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[acceptance]]
text = "Given a repository, when reindexed, then guide pages exist with names and commands filled and each page names its profile at the top and links to the other"
bound = false

[[acceptance]]
text = "Given a newer frob version, when reindexed, then the templates refresh and the diff is the template change only"
bound = false
+++

Implements navigation.md sections 3.1 and 4.1.

guide/README.md two entry points (New here, Working here), the four guide pages, and .gitattributes (linguist-generated, eol=lf), rendered with the repository's names and commands; every guide page states its profile at the top.
