+++
id = "01M48FXA11DET9Y49RVMEZV7TS"
title = "frob-check: COV001 reaches TypeScript tests (vitest/jest test_items) so TSX components count as covered"
type = "task"
category = "in-progress"
priority = "medium"
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T11:34:43Z"
updated = "2026-10-06T13:57:04Z"
scope = ["crates/frob-check/**"]

[[acceptance]]
text = "COV001 reaches src/api/client.ts::fetchUser from the test unit in client.test.ts (no COV001 finding on it) while the uncovered label, App and Button in the same run still fire"
bound = false
+++

crates/frob/tests/web_conformance.rs asserts COV001 fires on src/api/client.ts::fetchUser even though src/api/client.test.ts calls it inside a test() callback: COV001 does not consume the TypeScript test_items query. First real frob web rule. Found while working ~4M1BX5H.
