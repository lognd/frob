+++
id = "01M4MHB12DMANR5NYDY39JD2QC"
title = "crunk fix: preserve CRLF line endings when writing fixes"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-11T03:50:38Z"
updated = "2026-10-21T20:50:49Z"
scope = ["changelog.d/**", "crates/gob-fix/src/apply.rs", "crates/crunk-fix/tests/fix.rs"]

[[links]]
kind = "blocked-by"
target = "01M43ATCQVX9A1TJ6A4AE48FDX"

[[acceptance]]
text = "Given a CRLF file, when crunk fix writes it, then its line endings are preserved"
bound = false
+++

Split from ~80A3EXX: no 'crunk fix' writer exists in this tree yet (crates/crunk*), so the CRLF policy cannot be implemented or tested until it does. Blocked on the fix verb.
