+++
id = "01M1WJMD3C13MD8S1Y4H4Y44XW"
title = "refusal messages: state the self-citation remedy first, and always name a copy-pastable remedy for cross-ticket-leakage refusals"
type = "task"
flavour = "ux"
category = "done"
outcome = "duplicate"
priority = "low"
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T21:07:49Z"
aliases = ["T-4204"]
labels = ["milestone:1.1.0", "v1-cluster:F1"]
scope = ["src/frob/tickets"]

[[links]]
kind = "duplicates"
target = "01M4118NGH127F6DGVGS4GVE49"
+++

Consumer F-355 (T-4135), both items: (1) cross-ticket-leakage refusal when two tickets share a worktree doesn't name its remedy (close the other ticket in this worktree, or move its files out) even though the rule itself is correct; (2) a waiver whose live-tracker citation is this same closing ticket has exactly one sensible remedy (re-point/drop the citation in this same diff), but the generic two-remedy message lists 'file a successor ticket' first, which produced a junk ticket filed only to satisfy the gate. Fix: detect the self-citation case and state its one remedy outright; for the general case, always state a remedy, not just the rule. Fixture-testable: YES.
