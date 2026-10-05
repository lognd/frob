+++
id = "01M44YR0AAJ0X0BGXX7F17DMKH"
title = "unity evidence provider: batch-mode EditMode and PlayMode runs"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:37:04Z"
updated = "2026-10-05T02:37:04Z"
idempotency_key = "d94-unityrun"
scope = ["crates/frob-evidence/src/provider.rs", "crates/frob-evidence/src/record.rs", "crates/frob-evidence/src/verbs.rs", "crates/frob-evidence/tests/unity.rs", "crates/frob-tests/src/select.rs", "crates/frob-tests/src/run.rs", "crates/frob-tests/tests/**", "docs/reference/config.md", "docs/design/build-test-ci.md"]

[[links]]
kind = "blocked-by"
target = "01M44YQWGP5553K61QKC8HB0GQ"

[[links]]
kind = "blocked-by"
target = "01M44YQXBGJW1VKDF64YJ5RTJ6"

[[links]]
kind = "blocked-by"
target = "01M44YQZWPY9W2S61NW7TYPNJQ"

[[acceptance]]
text = "Given an NUnit 3 XML result with a passing and a failing test, when the provider parses it, then a measured record with both per-test results is stored"
bound = false

[[acceptance]]
text = "Given a change to a function reached only by a PlayMode test, when frob test runs, then the unity provider runs PlayMode for that assembly; given only EditMode tests are selected, then it runs EditMode"
bound = false

[[acceptance]]
text = "Given the project already open in another editor instance, when the provider runs, then it refuses with a remedy"
bound = false
+++

Second half of provider `unity`: run the editor `-batchmode -nographics -runTests -testPlatform EditMode|PlayMode -assemblyNames <asm> -testResults <file> -testFilter <ids>`, parse the NUnit 3 XML per test (test-case fullname, result, duration, failure message, output) into a measured record through gob-exec and the shared redact, scrub and escape paths. EditMode by default; PlayMode when the selected tests need it (assembly mode from the asmdef story, [UnityTest] and the PlayMode path), with the PlayMode graphics-less flag; one editor process per project at a time (a Unity project cannot be opened twice) with a clear refusal when the project is already open. Wires frob test selection for asmdef assemblies (select.rs). Reference: 274 [Test] and 17 [UnityTest] in the game repository. Docs: docs/reference/config.md, docs/design/build-test-ci.md.
