+++
id = "01M44YQWGP5553K61QKC8HB0GQ"
title = "Project model: Unity .asmdef and .asmref assemblies"
type = "story"
category = "in-progress"
priority = "high"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:37:00Z"
updated = "2026-10-08T05:30:24Z"
idempotency_key = "d94-asmdef"
scope = ["crates/gob-symbols/src/dotnet.rs", "crates/gob-symbols/src/unity_project.rs", "crates/gob-symbols/src/pipeline.rs", "crates/gob-symbols/tests/unity_project.rs", "docs/design/code-model.md", "docs/design/dotnet-unity.md", "crates/gob-symbols/src/crates.rs", "crates/gob-symbols/src/lib.rs"]

[[links]]
kind = "blocked-by"
target = "01M44YQSZ3YEXRDW9RKER9HRA2"

[[acceptance]]
text = "Given the Unity fixture with a runtime asmdef, an editor asmdef and a test asmdef that references them, when the package graph is built, then each asmdef is a package with the referenced-by edges and the test assembly is marked EditMode or PlayMode"
bound = false

[[acceptance]]
text = "Given an asmdef that references another by GUID, when the graph is built, then the reference resolves through the target's .meta file, and an unresolvable GUID is a finding, not a silent drop"
bound = false

[[acceptance]]
text = "Given an .asmref pointing at an asmdef, when files are assigned, then the asmref folder's files belong to that assembly"
bound = false

[[acceptance]]
text = "Given C# files outside any asmdef, when files are assigned, then they belong to Assembly-CSharp"
bound = false
+++

Unity project discovery in crates/gob-symbols/src/dotnet.rs (or unity_project.rs): Unity generates .csproj files and they are not committed, so assemblies come from .asmdef (name, references by name or GUID:<guid> resolved through the .meta of the referenced asmdef, includePlatforms, excludePlatforms, defineConstraints such as UNITY_INCLUDE_TESTS, precompiledReferences, overrideReferences, autoReferenced, allowUnsafeCode) and .asmref (reference to an asmdef that adds the files of its folder to it). Files below an asmdef folder belong to it until a nested asmdef; files with none belong to the implicit Assembly-CSharp (or -Editor, -firstpass) assembly. Each assembly maps to a package. An assembly with includePlatforms [Editor] is editor-only; one with UNITY_INCLUDE_TESTS and a UnityEngine.TestRunner reference is a test assembly, and its path (EditMode or PlayMode) decides the mode when the asmdef sets includePlatforms Editor. Library, Temp, obj and vendored trees outside Assets and Packages are ignored. Shape to cover from the game repository: 17 asmdefs, Hullbreach.Core at the root of the reference graph, 7 EditMode test assemblies and the Hullbreach.Demo.Tests PlayMode assembly with precompiledReferences nunit.framework.dll. Docs: docs/design/dotnet-unity.md section 1 and code-model.md.
