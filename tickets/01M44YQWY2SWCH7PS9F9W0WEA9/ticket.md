+++
id = "01M44YQWY2SWCH7PS9F9W0WEA9"
title = "dotnet evidence provider (TRX)"
type = "story"
category = "in-progress"
priority = "high"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:37:00Z"
updated = "2026-10-08T11:05:00Z"
idempotency_key = "d94-dotnetev"
labels = ["creates:crates/frob-evidence/tests/dotnet.rs", "creates:crates/gob-testsupport/src/bin/fake_dotnet.rs"]
scope = ["crates/frob-evidence/src/provider.rs", "crates/frob-evidence/src/config.rs", "crates/frob-evidence/src/record.rs", "crates/frob-evidence/src/error.rs", "crates/frob-evidence/src/verbs.rs", "crates/frob-evidence/src/scrub.rs", "crates/frob-evidence/Cargo.toml", "crates/frob-evidence/tests/dotnet.rs", "crates/gob-testsupport/src/lib.rs", "docs/reference/config.md", "docs/schemas/config.json", "docs/design/build-test-ci.md", "docs/design/tickets.md", "Cargo.lock", "crates/gob-testsupport/Cargo.toml", "crates/gob-testsupport/src/bin/fake_dotnet.rs", "docs/guides/quickstart.md", "crates/frob-evidence/src/lib.rs", "crates/frob-evidence/src/workspace.rs"]

[[links]]
kind = "blocked-by"
target = "01M44YQV7C3FYXB3QH20R4E5N8"

[[acceptance]]
text = "Given a C# test id, when ticket evidence add --provider dotnet runs, then a measured record with per-test results parsed from the TRX is stored"
bound = false

[[acceptance]]
text = "Given a TRX with a failed test whose message contains a secret-shaped string and non-ASCII text, when the record is stored, then the text is scrubbed and escaped"
bound = false

[[acceptance]]
text = "Given no dotnet SDK on the path, when the provider runs, then it refuses with a remedy and records nothing"
bound = false
+++

New provider `dotnet` in crates/frob-evidence (provider.rs beside nextest and pytest, config.rs, record.rs, error.rs, verbs.rs, tests/dotnet.rs): runs `dotnet test --logger trx` with a --filter built from test ids (FullyQualifiedName=...), parses the TRX per-test results (outcome, duration, error message, stdout) into a measured record, through gob-exec and the shared redact, scrub and escape paths (scrub.rs), allowlisted like pytest. A missing dotnet SDK refuses with a remedy. Tests use a portable test double for the dotnet binary (not a POSIX shell script, v1 broke on Windows with that). Docs: docs/reference/config.md and docs/schemas/config.json (`[evidence.dotnet]`), docs/design/build-test-ci.md and tickets.md provider list.
