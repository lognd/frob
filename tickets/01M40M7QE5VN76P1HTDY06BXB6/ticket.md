+++
id = "01M40M7QE5VN76P1HTDY06BXB6"
title = "nextest evidence inherits NEXTEST_PROFILE from the calling environment"
type = "bug"
category = "todo"
priority = "low"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T10:16:27Z"
updated = "2026-10-03T10:16:27Z"
idempotency_key = "m2-nextest-profile-leak"
labels = ["milestone:2"]
scope = ["crates/frob-evidence/**"]

[[acceptance]]
text = "Given NEXTEST_PROFILE set to a profile the target project lacks, when nextest evidence is captured, then it runs with the configured profile and records a measured pass"
bound = false
+++

Found on ~PFY7RCD: nextest exports NEXTEST_PROFILE to test processes, so an evidence capture spawned from inside a nextest run (or a shell that set it) runs the target project's nextest with a profile that project may not define, and records a failed measurement. The nextest provider should pass --profile from [evidence] nextest_profile explicitly and clear NEXTEST_PROFILE (and other NEXTEST_* variables that change selection) in the child environment through gob-exec. Test: with NEXTEST_PROFILE=ci in the environment and a project without that profile, evidence add with a matching filter records a measured pass.
