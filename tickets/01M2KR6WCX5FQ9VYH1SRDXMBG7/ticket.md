+++
id = "01M2KR6WCX5FQ9VYH1SRDXMBG7"
title = "Unity fixture project + e2e proof + docs/guides/unity.md"
type = "story"
flavour = "user_story"
category = "done"
outcome = "done"
priority = "medium"
parent = "01M2KR6WD1KXN9PGT16RCMBYFN"
reporter = "agent"
created = "2026-09-16T00:00:00Z"
updated = "2026-09-16T00:00:02Z"
aliases = ["T-4509"]
labels = ["milestone:0.533.0"]
scope = ["tests/fixtures/unity_sample/**", "tests/system/test_unity_e2e.py", "docs/guides/unity.md"]
+++

Story: capstone proof for the whole epic. blocked_by every prior story -- this is the final integration check and doc, run last after the resolver, capability maps, project model, and test evidence all exist.

Deliverables:
1. tests/fixtures/unity_sample/ -- a small Unity-shaped fixture: Assets/Scripts/ with a MonoBehaviour (Update + a coroutine via StartCoroutine), an Editor/ script using a UnityEditor-only API, a Runtime.asmdef and a Tests.asmdef with NUnit/[UnityTest] tests, and a minimal Packages/manifest.json + ProjectSettings/ProjectVersion.txt so project detection fires.
2. tests/system/test_unity_e2e.py -- scaffolds/inits the fixture, builds the graph, runs frob check and frob vet against it, and asserts the expected capability findings (net/fs.write/exec per the maps from stories 2-3) fire and that zero false positives appear on the fixture's clean code paths.
3. docs/guides/unity.md -- a user-facing guide: how to point frob at an existing Unity project, what gets detected, what capability findings to expect, how test evidence is gathered.

GIVEN the unity_sample fixture, WHEN 'frob scaffold unity-project' (or init detection) runs against it, THEN it succeeds and the asmdef-derived strata nodes match the fixture's two asmdef files.
GIVEN the fixture's MonoBehaviour and coroutine, WHEN frob check's dead-code/callgraph detectors run, THEN the lifecycle method and coroutine are NOT flagged as dead code (proves story 3's roots).
GIVEN the fixture's Editor-only API call and the fixture's BCL/Unity API calls (net, fs.write), WHEN frob vet runs, THEN exactly the expected findings appear, tagged correctly (editor-only vs runtime), with zero unexpected findings.
GIVEN the fixture's NUnit and [UnityTest] tests, WHEN test evidence collection runs (T-4517/T-4508), THEN both are collected and bindable, proving stories 1-5 compose end to end.

## Unblock log
- 2026-09-19: unblocked by T-4506 -- leaves landed or queued; capstone can proceed against dev
- 2026-09-19: unblocked by T-4511 -- leaves landed or queued; capstone can proceed against dev
- 2026-09-19: unblocked by T-4514 -- leaves landed or queued; capstone can proceed against dev
- 2026-09-19: unblocked by T-4518 -- leaves landed or queued; capstone can proceed against dev
- 2026-09-19: unblocked by T-4516 -- leaves landed or queued; capstone can proceed against dev
