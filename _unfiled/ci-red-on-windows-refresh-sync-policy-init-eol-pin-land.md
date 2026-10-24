+++
id = "01M5PC8M49F53YSPKKT7XXMDFH"
title = "CI red on Windows: refresh/sync_policy/init_eol_pin/land/ledger-refresh/csharp snapshot tests fail"
type = "bug"
category = "in-progress"
priority = "high"
points = 5
reporter = "lognd"
created = "2026-10-24T07:16:07Z"
updated = "2026-10-24T08:31:29Z"
scope = ["crates/frob-cli/**", "crates/frob/**", "crates/frob-ledger/**", "crates/frob-land/**", "crates/crunk/**", "crates/gob-symbols/**", "crates/gob-walk/**"]

[[acceptance]]
text = "The nextest step of the rust (windows-latest) CI job passes on experimental"
bound = true
+++

Failing tests in CI run 40069211396 job rust (windows-latest); log at /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/win.log. Diagnose per test (path separators, CRLF, git on Windows) and fix without weakening tests.
