+++
id = "01M44YQVN6PMK0D8NJ801ENJEW"
title = "C# fixtures, corpus and fidelity row, end to end frob check"
type = "story"
category = "todo"
priority = "high"
points = 3
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:36:59Z"
updated = "2026-10-05T02:36:59Z"
idempotency_key = "d94-fixture"
scope = ["crates/gob-symbols/tests/**", "crates/frob-check/tests/**", "docs/reference/fidelity.md", "docs/design/code-model.md"]

[[links]]
kind = "blocked-by"
target = "01M44YQTCDPH87ASRMSJEN2C8Q"

[[links]]
kind = "blocked-by"
target = "01M44YQTSWW9EH49541MY9A7AX"

[[links]]
kind = "blocked-by"
target = "01M44YQV7C3FYXB3QH20R4E5N8"

[[acceptance]]
text = "Given the C# fixture corpus, when the gob-symbols conformance tests run, then symbols, imports, calls and test ids match the checked-in snapshots"
bound = false

[[acceptance]]
text = "Given the fixture solution, when frob check runs end to end, then it exits with the expected findings and no panic"
bound = false

[[acceptance]]
text = "Given docs/reference/fidelity.md, when read, then a C# row exists and every cell is Implemented, NotApplicable with a reason, or Gap with a ticket"
bound = false
+++

Fixture and conformance work in crates/gob-symbols/tests (csharp.rs, corpus/, snapshots/) and crates/frob-check/tests: a small .NET solution (two projects, partial type, extension method, NUnit and xUnit tests, #if branches) and a Unity-shaped fixture (a MonoBehaviour with Awake and Update, [SerializeField] field, [UnityTest], asmdef pair) synthesized from the shapes seen in the owner's game repository, never copied from it. Adds the C# row to the fidelity table (docs/reference/fidelity.md) with each cell Implemented, NotApplicable(reason) or Gap(ticket), plus one end-to-end frob check run over the fixture. Update docs/design/code-model.md adapter list.
