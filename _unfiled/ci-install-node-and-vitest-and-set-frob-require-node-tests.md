+++
id = "01M4A48FTHZAZXNRMTZ20D00X3"
title = "CI: install node and vitest and set FROB_REQUIRE_NODE_TESTS so the TypeScript runner tests never skip"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-07T02:49:39Z"
updated = "2026-10-22T02:27:14Z"
scope = ["crates/gob-dev/**"]

[[acceptance]]
text = "ci.yml and cargo dev ci install node and set FROB_REQUIRE_NODE_TESTS=1, mirroring REQUIRE_PYTHON_TESTS_ENV"
bound = false

[[acceptance]]
text = "the node-required env makes a missing node fail the TypeScript runner tests instead of skipping"
bound = false
+++

found while working ~RNQ92ZK: the verb-level vitest and jest test skips with a named message when node is absent (node is absent on the quasar helper); cargo dev ci and ci.yml should install node and set FROB_REQUIRE_NODE_TESTS=1 like FROB_REQUIRE_PYTHON_TESTS (REQUIRE_PYTHON_TESTS_ENV in crates/gob-dev/src/ci.rs). A real-vitest end-to-end test (npm install of a pinned vitest) can follow.
