+++
id = "01M2KR6WD1KXN9PGT16RCMBYFN"
title = "C# and Unity support for frob (owner directive 2026-09-16)"
type = "epic"
category = "triage"
priority = "low"
points = 1
reporter = "agent"
created = "2026-09-16T00:00:00Z"
updated = "2026-10-04T21:08:54Z"
aliases = ["T-4513"]
labels = ["v1-cluster:D2", "triage:accepted"]
scope = ["tickets/T-CSUNITY-EPIC/**"]
+++

Owner directive 2026-09-16: bring C# to end-to-end parity and add Unity support (Unity project model, .NET BCL + Unity API capability maps, NUnit/UnityTest evidence, fixture project). See design doc / stories for measured starting state: no C# capability resolver wired into _capability_scan.py, no NUnit/UnityTest collector, T-3232/T-3234/T-3856 are prerequisite cross-cutting bugs (linked, not duplicated), T-1597/T-1598 are the general umbrella (not duplicated -- this epic pulls C#/Unity out of that backlog per owner priority).

frob:outcome-metric all children done (5/5: T-4506, T-4509, T-4516, T-4518, T-4561); C# and Unity support landed end-to-end (adapter parity, fixture project, test-evidence collection, project model, post-land COV002 residue closed).
