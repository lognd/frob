+++
id = "01M35RZY8004GBMBN5HEN9ZYDA"
title = "ARCH001 self-check fails: fleet_status._ticket_readiness_lines redundant with test-side declaration (T-4710)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5376"]
labels = ["milestone:0.534.0"]
scope = ["tests/system/test_fleet_status_ticket_readiness_arch001.py", "scripts/fleet_status.py"]
+++

CI run 35819358270 (ubuntu/macos/windows, dev 7d7e0ae4d4); re-verified on dev tip 39b89ed091: tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding fails -- frob-arch reports fleet_status.py::_ticket_readiness_lines as redundant with an existing test-side declaration (T-4710 remnant), tripping ARCH001 on frob's own repo. Not covered by any open ticket I could find; filed fresh per T-4758-style sweep.
