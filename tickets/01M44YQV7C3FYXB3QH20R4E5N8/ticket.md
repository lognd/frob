+++
id = "01M44YQV7C3FYXB3QH20R4E5N8"
title = "C# test detection: NUnit, xUnit, MSTest, UnityTest"
type = "story"
category = "in-progress"
priority = "high"
points = 3
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:36:58Z"
updated = "2026-10-08T06:24:43Z"
idempotency_key = "d94-tests"
scope = ["crates/gob-symbols/src/csharp.rs", "crates/gob-symbols/src/lib.rs", "crates/frob-tests/src/catalog.rs", "crates/frob-tests/tests/**", "crates/gob-symbols/tests/csharp.rs"]

[[links]]
kind = "blocked-by"
target = "01M44YQSZ3YEXRDW9RKER9HRA2"

[[acceptance]]
text = "Given C# classes using NUnit, xUnit and MSTest attributes, when the catalog is built, then each attributed method is a test with its fully qualified name as id"
bound = false

[[acceptance]]
text = "Given a [UnityTest] coroutine method and a [SetUp] method, when the catalog is built, then the former is a test (flagged PlayMode-capable) and the latter is not"
bound = false

[[acceptance]]
text = "Given a C# method called only by tests, when COV001 runs, then it counts as reached by those tests"
bound = false
+++

Test-shape detection in crates/gob-symbols (csharp.rs, mirrored by `is_python_test_fn` style helpers exported from lib.rs) and crates/frob-tests/src/catalog.rs: NUnit ([Test], [TestCase], [TestCaseSource], [UnityTest]), xUnit ([Fact], [Theory]) and MSTest ([TestMethod]). [SetUp], [TearDown], [UnitySetUp] are fixtures, not tests. A test id is the fully qualified method name (Namespace.Type.Method), the form both runners filter by; parameterized cases keep the method id. A test file is recognised by test attributes, not by path alone (Unity keeps tests under Assets/Tests/EditMode and Assets/Tests/PlayMode). Game fixture shape to mirror: 274 [Test] and 17 [UnityTest] across 43 files in 8 test assemblies.
