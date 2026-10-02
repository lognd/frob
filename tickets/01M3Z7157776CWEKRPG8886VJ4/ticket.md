+++
id = "01M3Z7157776CWEKRPG8886VJ4"
title = "grimble-ci: CI001-015 and DK001-004"
type = "task"
category = "todo"
priority = "medium"
points = 8
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:26Z"
updated = "2026-10-02T21:06:26Z"
idempotency_key = "m2-ci"
labels = ["milestone:2"]
scope = ["crates/grimble-ci/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z712WWYRXPSWNVDXX6K71R"

[[links]]
kind = "blocked-by"
target = "01M3Z713YNM5666B7YFEHPFVKD"

[[links]]
kind = "blocked-by"
target = "01M3Z71542Y6NZG3G8A83EFRF2"

[[acceptance]]
text = "Given a workflow without top-level permissions and a job without timeout-minutes, when grimble check runs, then CI002 and CI005 fire with the measured remedy"
bound = false
+++

cicd.md section 5: the owned policy and consistency rules over the Actions and Dockerfile adapters, with the bound-tool overlaps delegated to the zizmor and actionlint stages; CI012 joins CI with manifests through the F2 manifest adapter.
