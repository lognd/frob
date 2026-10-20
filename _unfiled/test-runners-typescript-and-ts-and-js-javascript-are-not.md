+++
id = "01M3DG64CHWHEGXVF4YG762T83"
title = "test runners: 'typescript' and 'ts' (and js/javascript) are not aliased, so vitest evidence never binds; one canonical language table + loader refusal"
type = "bug"
category = "todo"
priority = "low"
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-10-09T20:42:46Z"
aliases = ["T-6545"]
labels = ["v1-cluster:C4a", "triage:accepted"]
scope = ["src/frob/testing/_collect.py", "tests/unit/test_runner_language_aliases.py", "docs/design/testing.md"]
+++

Source: logand.app-v2 FROBLEMS.md F-410 (peer coordinator report, 2026-09-26, frob 0.531.1.dev332).

The vitest collector keys TypeScript as 'ts' in LANGUAGE_COLLECTORS, while frob.toml files (and the docs since 0.530) use `[[test.runner]] language = "typescript"`. Nothing aliases the two, so every vitest evidence bind fails with "language 'ts' has selected tests but no runner" followed by EvidenceNotPassing, even though the collector does find the ids (.frob/vitest-collect.json). Deliver: (1) one canonical language-name table shared by the collectors, the runner config and frob.lang (typescript/ts, javascript/js, python/py, csharp/cs, rust/rs) with aliases resolved at config load; (2) the frob.toml loader refuses an unknown `language` key with the canonical name and the accepted aliases in the message; (3) positive control: a frob.toml with language = "typescript" binds a vitest id, and one with language = "tsx" is refused with the pointer.


Follow-ons from the same report (logand F-410, after switching to language = "ts"):

4. Vitest verification always FAILS: `_expand_placeholder("{files}", ...)` in testing/_runners.py renders the full evidence id (`path::describe > name`) into the vitest argv; vitest treats it as a file filter, exits 1, and `_verify_one_bucket_passing` reports FAILED -- exactly the `{files}` shape docs/modules/testing.md documents for TS, so no granular vitest evidence can ever verify. Deliver: split a vitest/jest id into the file path plus `-t "<describe > name>"` (or add a `{names}` placeholder rendered per runner), with a positive control that a `path::describe > name` id passes verification against a fixture vitest project and a wrong name fails.

5. `select_tests`'s suite-wide fallback hardcodes "typescript" in its language list, so after the key change a frob.toml-only diff selects no TS runner: the canonical table from (1) must feed this list too; positive control: a frob.toml-only change in a fixture with language = "ts" selects the vitest runner.
