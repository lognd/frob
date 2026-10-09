+++
id = "01M44YQZWPY9W2S61NW7TYPNJQ"
title = "unity evidence provider: editor discovery and refusal"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:37:03Z"
updated = "2026-10-09T04:17:08Z"
idempotency_key = "d94-unityedit"
labels = ["creates:crates/gob-testsupport/**"]
scope = ["crates/frob-evidence/src/provider.rs", "crates/frob-evidence/src/config.rs", "crates/frob-evidence/src/error.rs", "crates/frob-evidence/tests/unity.rs", "docs/reference/config.md", "docs/schemas/config.json", "crates/frob-evidence/src/workspace.rs", "crates/frob-evidence/src/lib.rs", "crates/gob-testsupport/**"]

[[links]]
kind = "blocked-by"
target = "01M44YQWGP5553K61QKC8HB0GQ"

[[links]]
kind = "blocked-by"
target = "01M44YQWY2SWCH7PS9F9W0WEA9"

[[acceptance]]
text = "Given ProjectVersion.txt naming 6000.0.43f1 and no editor at any Hub location, when the provider runs, then it refuses naming that version and the [evidence.unity] editor key"
bound = true

[[acceptance]]
text = "Given [evidence.unity] editor set to a path, when the provider runs, then that path is used regardless of the version file"
bound = true

[[acceptance]]
text = "Given an editor that reports no valid license, when the provider runs, then it refuses with a remedy and records nothing"
bound = true
+++

First half of provider `unity` in crates/frob-evidence (provider.rs, config.rs, error.rs, tests/unity.rs): resolve the editor path from `[evidence.unity] editor`, defaulting to the version in ProjectSettings/ProjectVersion.txt under the standard Unity Hub install locations (Windows C:/Program Files/Unity/Hub/Editor/<ver>/Editor/Unity.exe, macOS /Applications/Unity/Hub/Editor/<ver>/..., Linux ~/Unity/Hub/Editor/<ver>/Editor/Unity); a missing editor or missing, expired or unavailable license refuses with a remedy naming the version and the config key, never a silent skip. Tests use a portable fake editor. Docs: docs/reference/config.md, docs/schemas/config.json.
