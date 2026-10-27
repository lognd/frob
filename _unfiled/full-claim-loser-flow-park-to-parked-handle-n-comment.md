+++
id = "01M5DBVTFBQCV375510SMKSNHT"
title = "Full claim-loser flow: park to parked/<handle>-<n>, comment, requeue hint"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T19:15:58Z"
updated = "2026-10-27T02:58:31Z"
+++

found while working ~46BECG2. E-CLAIM-LOST currently only refuses and releases the lease. Design 3.3: push local commits to parked/<handle>-<n>, write a comment event, report 'claim lost to <actor> at <oid>' on sync.
