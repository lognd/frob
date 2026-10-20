+++
id = "01M336K75FCD98TE5R6G3RDK2Z"
title = "DOC006 no longer flags backticked future-verb phrasing in ticket bodies"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5295"]
labels = ["milestone:0.534.0"]
scope = ["tests/unit/test_ticket_2691_doc006.py", "src/frob/gates/_docptr.py"]
+++

gh run 35717833933; re-verified on dev tip 3acf8c6b30: TestTicket2691Doc006Regression::test_backticked_future_verb_is_flagged and TestTicket2742Doc006Regression::test_backticked_future_verb_is_flagged both fail (found == []). Captured log shows load aborted: ticket.md malformed frontmatter -- ticket-queue load failure inside the gate now swallows the DOC006 exemption path entirely instead of flagging.
