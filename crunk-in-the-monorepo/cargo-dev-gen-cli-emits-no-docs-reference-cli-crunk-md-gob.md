+++
id = "01M5EQAG7SXNJQ521RRZ2T166E"
title = "cargo dev gen cli emits no docs/reference/cli/crunk.md (gob-dev links crunk only as a dev-dependency)"
type = "bug"
category = "todo"
priority = "medium"
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-21T07:55:27Z"
updated = "2026-10-21T07:55:27Z"
labels = ["area:crunk"]
scope = ["crates/gob-dev/**"]
+++

found while working ~CDYEYV6: docs/reference/cli has only any.md and frob.md; the crunk verb inventory is never generated, so docs/crunk/migration.md points at crunk --help instead of a generated page.
