+++
id = "01M6R10T8S2185AFPNXCYCWMPV"
title = "CI: free disk on the windows rust job before the gen step (runner hit 8 MB free)"
type = "chore"
category = "todo"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-11-06T08:53:47Z"
updated = "2026-11-06T09:46:34Z"
labels = ["no-story"]

[[acceptance]]
text = "The windows rust job frees disk space before the 'cargo dev ci --step gen' step so it no longer fails with ENOSPC"
bound = false
+++

Run 42184030955 windows rust job passed 7174 tests then failed in 'cargo dev ci --step gen' with 'no space on device' (8 MB free). Free disk or trim target between steps (drop test binaries/incremental, or move target to D:). Reason for no-story: CI infra chore. Scope: .github/workflows/**
