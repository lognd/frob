+++
id = "01M1WJMD4F17WBERSCHDHZ6KRV"
title = "bind a shell component to its runtime image and shellcheck/lint it with that image's actual dialect"
type = "task"
category = "todo"
priority = "low"
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T22:22:23Z"
aliases = ["T-4239"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/strata"]
+++

Consumer F-325/M2-6: a script's shebang says sh, its declared runtime image is alpine (busybox userland), and shellcheck ran with the default sh dialect misses a non-POSIX GNU extension (head -n -N). Bind a shell component to its runtime image (a strata node attribute) and run shellcheck with the matching dialect/compat list, or run the script's own tests inside that image. Not fixture-testable in frob's own tree: no shell-scripts-bound-to-container-images exist here.
