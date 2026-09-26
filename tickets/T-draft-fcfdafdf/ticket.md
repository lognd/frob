---
id: T-draft-fcfdafdf
title: 'frob check: csharp/unity project type -- detection via detect_unity_project
  or *.asmdef and a dispatcher that runs gates plus a configurable [[test.runner]]
  step'
state: queued
kind: feature
origin: agent
created: '2026-09-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/check/__init__.py
- src/frob/app/check_runner.py
- src/frob/lang/_project_detect.py
- src/frob/app/config.py
- docs/modules/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the project-hullbreach session (2026-09-26), blocking the owner's
Unity 6 game repo. `frob scaffold unity-project .` works (frob.toml plus one
design/unity_*.strata per asmdef), but `frob check` and `frob check --only
gates` exit 1 at once with CHECK001 "unknown project type: 'unknown' (no
dispatchable language stage)". Verified on dev b41443f46d:
`frob.check.detect_project_type` returns only python/cpp/rust/typescript/
unknown and `check_runner._DISPATCH_BY_TYPE` has the same four entries;
`frob.lang._project_detect.detect_unity_project` exists (T-4518) but neither
consults it, although T-4506 (C# adapter parity), T-4518 (Unity project
model) and T-4516 (NUnit collection) are done.

Deliver:
1. Detection: a root with Assets/ + ProjectSettings/ProjectVersion.txt
   (detect_unity_project) or any *.asmdef resolves to "unity"; a root with
   a .sln/.csproj and no Unity markers resolves to "csharp". `frob check
   --type unity|csharp` accepted.
2. Dispatch: `_DISPATCH_BY_TYPE["unity"]` and `["csharp"]` run the gates
   stage (strata, tickets, docs, policy) exactly like the other types, then
   an OPTIONAL build/test step taken from `[[test.runner]]` in frob.toml.
   Unity roots have no project file, so no `dotnet test .` default: with no
   runner configured the step is skipped with one INFO line naming the
   config key; the scaffolded unity-project runner must not assume dotnet.
   (hullbreach runs `tools/plaincs/run_tests.sh`, a hand-written net8
   csproj over Assets/Scripts.)
3. `--only gates` on a unity/csharp root never touches the runner.
4. Positive control: a fixture Unity root (Assets/, ProjectSettings/
   ProjectVersion.txt, one asmdef, one strata fragment) where `frob check
   --only gates` exits 0 and a planted strata error is reported; a second
   run with a `[[test.runner]]` that exits 3 propagates the failure.
5. Docs: docs/modules/check.md lists the two new types and the runner key.
Follow-on: T-5198 (unity-project strata fragments have no root module) is
expected to fire on a real repo right after this; leave it to that ticket.
