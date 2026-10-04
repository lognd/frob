+++
id = "01M43AVT63Y3EBQKJD3KA6NR6P"
title = "OWNER STEP: import crunk tickets and archive lognd/crunk"
type = "chore"
category = "todo"
priority = "medium"
points = 1
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:30:23Z"
updated = "2026-10-04T11:30:23Z"
idempotency_key = "crunk-plan-owner_archive"
labels = ["area:crunk", "owner"]
scope = ["docs/crunk/retire.md"]

[[links]]
kind = "blocked-by"
target = "01M43AVKZWSTQRGWR6YPXH7THX"

[[links]]
kind = "blocked-by"
target = "01M43AVMN1DWBVTYW37JBTM6EF"

[[links]]
kind = "blocked-by"
target = "01M43AVST360F0CWT84HAYNTD7"

[[acceptance]]
text = "Given the import run, when tickets are listed with component crunk, then open ones match the reviewed dry-run"
bound = false

[[acceptance]]
text = "Given the lognd/crunk repository, when opened, then it is archived and its README points to this repository"
bound = false

[[acceptance]]
text = "Given frob.toml, when read, then crunk is no longer a preview product"
bound = false
+++

Owner only. After parity and the PyPI switch: review the dry-run of the selective import ticket and run it, add a README notice to lognd/crunk pointing here, archive the GitHub repository, and remove crunk from [release] preview. Nothing is deleted.
