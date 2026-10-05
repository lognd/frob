+++
id = "01M44YR0QRN65R7RNDQ35YNWMZ"
title = "Prove the unity provider on the Windows editor through goway"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:37:04Z"
updated = "2026-10-05T02:37:04Z"
idempotency_key = "d94-goway"
scope = ["docs/guides/unity.md"]

[[links]]
kind = "blocked-by"
target = "01M44YR0AAJ0X0BGXX7F17DMKH"

[[acceptance]]
text = "Given a Windows host with the Unity editor, when the unity provider runs an EditMode and a PlayMode fixture test through goway, then a measured record with both results is attached to this ticket"
bound = false

[[acceptance]]
text = "Given a failure in either run, when the proof ends, then a bug ticket exists naming the failing step"
bound = false
+++

Manual proof task, no product code: with a Unity 6000.0.43f1 editor installed on the owner's Windows side, run the unity provider against a Unity fixture project once through goway (one run at a time, per the goway-offload and disk-guard constraints) for one EditMode and one PlayMode test, and record the result as bound evidence on this ticket plus a short note in docs/guides (transcript with redacted paths). Failures become bug tickets against the unity provider story.
