+++
id = "01M44YQY6KR3NCCNGKJ9QK3N9A"
title = "unity pack: serialized fields have an external writer"
type = "story"
category = "todo"
priority = "medium"
points = 3
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:37:01Z"
updated = "2026-10-05T02:37:01Z"
idempotency_key = "d94-serial"
scope = ["packs/unity.toml", "crates/gob-ir/**", "crates/frob-obligations/**", "docs/design/packs.md"]

[[links]]
kind = "blocked-by"
target = "01M44YQXS4BXE0X07FBYR0STJ5"

[[acceptance]]
text = "Given a private [SerializeField] field never assigned in code, when effect and flow rules run with the pack enabled, then the field has an external writer and is not reported as never written"
bound = false

[[acceptance]]
text = "Given a [NonSerialized] public field never assigned, when the rules run, then it is still reported"
bound = false

[[acceptance]]
text = "Given the pack disabled, when the rules run, then a [SerializeField] field never assigned is reported"
bound = false
+++

Second vocabulary of the unity pack: [SerializeField] fields and public instance fields of MonoBehaviour and ScriptableObject types (not [NonSerialized], not static, not properties without [field: SerializeField]) are written from outside the code (scenes, prefabs, the Inspector), so effect and flow rules see an external writer and a never-assigned warning does not fire. Sites: packs/unity.toml vocabulary rows, the effect and flow rule readers in crates/frob-obligations and crates/gob-ir eval. Reference shape: 79 [SerializeField] fields in the game repository. Docs: docs/design/packs.md vocabulary table.
