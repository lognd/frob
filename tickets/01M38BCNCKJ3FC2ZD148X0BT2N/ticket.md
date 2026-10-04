+++
id = "01M38BCNCKJ3FC2ZD148X0BT2N"
title = "Route ticket-runner CLI to run_dotnet_tests/run_unity_batchmode for csharp/unity node ids"
type = "task"
category = "triage"
priority = "medium"
points = 3
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-04T21:07:01Z"
aliases = ["T-5523"]
labels = ["milestone:v0.534.0", "v1-cluster:C4a"]
scope = ["src/frob/app/ticket_runner/__init__.py"]

[[links]]
kind = "duplicates"
target = "01M38BCNBFK7KWQYW6DSDFS36Z"
+++

Found draining CI run 35951365410 (windows-latest self-gate, dev 9e0c89bb19),
but the underlying finding is not Windows-specific (WIRE002 is a static
waiver-vs-ledger check, verified to reproduce on this Linux checkout too):

- src/frob/testing/_dotnet_runner.py:179 and
  src/frob/testing/_unity_batchmode.py:224 each carry
  frob:waive WIRE001 ... follow_up="T-4516", but T-4516 is done (and its
  blocker T-4518 is also done) -- WIRE001 waivers must bind to a real, OPEN
  follow-up ticket (WIRE002).

- src/frob/webapp/_a11y_statement.py:138 has the same shape
  (follow_up="T-5454", also done) but that file is out of this ticket's
  scope (webapp is off-limits for this drain) -- leaving it for whichever
  ticket owns webapp/** to repoint or waive separately.

The waived gap itself (routing frob's ticket-runner CLI to call
run_dotnet_tests/run_unity_batchmode for csharp/unity node ids) never got
its own open follow-up ticket when T-4516/T-4518 closed -- file one now and
repoint both waivers' follow_up= to it.

frob:tests tests/unit/test_dotnet_runner.py, tests/unit/test_unity_batchmode.py
