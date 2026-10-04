+++
id = "01M3AXSDAY1ZEKSEM4W10KB909"
title = "dropped: runtime cache-stampede-under-load detection (research row 8.3)"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
parent = "01M3AXSD815BE5WXEJ8JDTSV9J"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:01Z"
aliases = ["T-6494"]
labels = ["milestone:0.539.0"]
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: dropped: runtime cache-stampede-under-load detection (research row 8.3)
kind: feature
tier: dropped
parent: T-SYS-SH
scope: --
blocked_by: []

Reason: research row 8.3 ("Cache stampede protection") is explicitly tagged dynamic-only in
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->scratchpad/sysdesign-research.md's tag column: "Hot-key cache-read code with no single-flight/
lock guard around the recompute-on-miss path flags a stampede risk when the design model marks
the key as high-QPS | dynamic-only". Per the owner stance, dynamic-only rows become a
frob:tests obligation, never a static rule -- actually detecting a stampede requires runtime
load, which no static analysis can observe. The declared-vs-observed STATIC companion (does the
design declare and prove a `stampede_guard`) is a legitimately different, separately justified
check and is filed as SYSDESIGN304/305 (T-SYS-E-STAMPEDE), not dropped.
