+++
id = "01M38BCNCM2FNACEBE1ZKNXRJF"
title = "WIRE002: repoint stale WIRE001 waivers in dotnet/unity runners off done ticket T-4516"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5524"]
labels = ["milestone:v0.534.0"]
scope = ["src/frob/testing/_dotnet_runner.py", "src/frob/testing/_unity_batchmode.py"]
+++

Found draining CI run 35951365410 (windows-latest self-gate, dev 9e0c89bb19).
Not Windows-specific -- WIRE002 is a static waiver-vs-ledger check, verified
to reproduce on this Linux checkout at the same commit too.

src/frob/testing/_dotnet_runner.py:179 and
src/frob/testing/_unity_batchmode.py:224 each carry
frob:waive WIRE001 ... follow_up="T-4516", but T-4516 is done (its blocker
T-4518 is also done) -- WIRE001 waivers must bind to a real, OPEN follow-up
ticket (WIRE002).

Fix: repoint both waivers' follow_up= to T-5523 (just filed: "Route
ticket-runner CLI to run_dotnet_tests/run_unity_batchmode for csharp/unity
node ids"), which now owns the still-open gap the waivers describe.

src/frob/webapp/_a11y_statement.py:138 has the identical shape
(follow_up="T-5454", also done) but webapp/** is out of scope for this
drain -- left for whichever ticket owns webapp/** to repoint separately.

frob:tests tests/unit/test_dotnet_runner.py, tests/unit/test_unity_batchmode.py

frob:no-behavior-change reason="comment-only fix: repoints a stale WIRE001 waiver follow_up= from a done ticket (T-4516) to the open ticket that now owns the gap (T-5523); no runtime code changed"
