+++
id = "01M2KR6WD4TNTKQN6H150PQT1A"
title = "Test evidence: NUnit + Unity Test Framework collection and runners"
type = "story"
flavour = "user_story"
category = "done"
outcome = "done"
priority = "medium"
points = 1
parent = "01M2KR6WD1KXN9PGT16RCMBYFN"
reporter = "agent"
created = "2026-09-16T00:00:00Z"
updated = "2026-09-16T00:00:02Z"
aliases = ["T-4516"]
labels = ["milestone:0.533.0"]
scope = ["src/frob/testing/_collect_csharp.py", "src/frob/testing/_runners.py"]

[[links]]
kind = "blocked-by"
target = "01M2KR6WD6C92T9DZKW5R2TR0A"
+++

Story: collect and run C#/Unity tests as evidence bindable by frob:tests directives. Parent for the two leaves below. blocked_by T-4518 because the Unity-vs-plain-C# distinction (asmdef, test assembly) needs project-model detection to route correctly.
