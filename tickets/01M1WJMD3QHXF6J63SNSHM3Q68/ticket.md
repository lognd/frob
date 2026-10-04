+++
id = "01M1WJMD3QHXF6J63SNSHM3Q68"
title = "gate: a dynamically-resolved import/reference resolving to a path unreachable from the shipped artifact is a finding, not an accepted OPAQUE001 waiver"
type = "task"
category = "todo"
priority = "low"
parent = "01M1WJMD1X14Z9P76XPX0QQ0NM"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T22:22:23Z"
aliases = ["T-4215"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates/_opaque.py"]
+++

Consolidates T-4157/H4-1 second half (a JS @vite-ignore dynamic import whose specifier resolves under src/ but is not reachable from the built output; cheaply approximated as 'no built artifact may contain the literal /src/') with T-4175/P2 (the same shape via a Python importlib string-target and a Dockerfile COPY operand -- 'the target module genuinely does not exist yet' legitimised by an OPAQUE001 waiver). Same underlying question across three runtimes: does a dynamically-resolved specifier land somewhere the shipped artifact actually contains. Adjacent to T-4160 (also OPAQUE001, opposite defect: a false POSITIVE on a type-position import) -- different mechanism, same gate file, worth sequencing together. Not fixture-testable in frob's own tree: no bundler/Docker build target exists here.
