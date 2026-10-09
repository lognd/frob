+++
id = "01M3DG64DYDB3WZKETCM7XBF7P"
title = "frob check: csharp/unity project type -- detection via detect_unity_project or *.asmdef and a dispatcher that runs gates plus a configurable [[test.runner]] step"
type = "task"
category = "todo"
priority = "low"
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-10-09T20:42:52Z"
aliases = ["T-6590"]
labels = ["v1-cluster:C4a", "triage:accepted"]
scope = ["src/frob/check/__init__.py", "src/frob/app/check_runner.py", "src/frob/lang/_project_detect.py", "src/frob/app/config.py", "docs/modules/check.md", "docs/design/rules.md"]
+++

Reported by the project-hullbreach session (2026-09-26), blocking the owner's
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->Unity 6 game repo. `frob scaffold unity-project .` works (frob.toml plus one
design/unity_*.strata per asmdef), but `frob check` and `frob check --only
gates` exit 1 at once with CHECK001 "unknown project type: 'unknown' (no
dispatchable language stage)". Verified on dev b41443f46d:
`frob.check.detect_project_type` returns only python/cpp/rust/typescript/
unknown and `check_runner._DISPATCH_BY_TYPE` has the same four entries;
`frob.lang._project_detect.detect_unity_project` exists (T-4518) but neither
consults it, although T-4506 (C# adapter parity), T-4518 (Unity project
model) and T-4516 (NUnit collection) are done.

Deliver:
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->1. Detection: a root with Assets/ + ProjectSettings/ProjectVersion.txt
   (detect_unity_project) or any *.asmdef resolves to "unity"; a root with
   a .sln/.csproj and no Unity markers resolves to "csharp". `frob check
   --type unity|csharp` accepted.
2. Dispatch: `_DISPATCH_BY_TYPE["unity"]` and `["csharp"]` run the gates
   stage (strata, tickets, docs, policy) exactly like the other types, then
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->   an OPTIONAL build/test step taken from `[[test.runner]]` in frob.toml.
   Unity roots have no project file, so no `dotnet test .` default: with no
   runner configured the step is skipped with one INFO line naming the
   config key; the scaffolded unity-project runner must not assume dotnet.
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->   (hullbreach runs `tools/plaincs/run_tests.sh`, a hand-written net8
   csproj over Assets/Scripts.)
3. `--only gates` on a unity/csharp root never touches the runner.
4. Positive control: a fixture Unity root (Assets/, ProjectSettings/
   ProjectVersion.txt, one asmdef, one strata fragment) where `frob check
   --only gates` exits 0 and a planted strata error is reported; a second
   run with a `[[test.runner]]` that exits 3 propagates the failure.
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->5. Docs: docs/modules/check.md lists the two new types and the runner key.
Follow-on: T-5198 (unity-project strata fragments have no root module) is
expected to fire on a real repo right after this; leave it to that ticket.
