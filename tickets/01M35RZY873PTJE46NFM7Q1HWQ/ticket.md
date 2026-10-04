+++
id = "01M35RZY873PTJE46NFM7Q1HWQ"
title = "test_tickets_triage_dates.py fixtures use a semver-shaped sprint label, refused by T-5133's SprintIsSemverShaped"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5383"]
labels = ["milestone:0.534.0"]
scope = ["tests/test_tickets_triage_dates.py"]
+++

CI run 35819358270 (ubuntu/macos); re-verified failing on dev tip 39b89ed091: tests/test_tickets_triage_dates.py::TestSetSprintRecordsTriageChange::test_assigning_a_sprint_records_a_triage_change_entry, test_reassigning_the_same_sprint_still_records_an_entry, and test_reloaded_ticket_carries_the_recorded_entry all fail with Err(TicketError.SprintIsSemverShaped) -- each calls set_sprint(tmp_path, ticket_id, 'v0.531.0'), a semver-shaped label, which T-5133 (landed 2026-09-22 evening, BRIEF item 12) now refuses since a sprint must be goal-named and a version belongs in --milestone. Fix: change the fixtures' sprint label to a goal-named string (e.g. 'burn-down') so the tests exercise set_sprint's real contract again.
