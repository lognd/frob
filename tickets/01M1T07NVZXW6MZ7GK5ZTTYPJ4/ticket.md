+++
id = "01M1T07NVZXW6MZ7GK5ZTTYPJ4"
title = "RESULT001: network-I/O async def may not return None"
type = "security"
category = "todo"
priority = "low"
parent = "01M1QDTYV6Z35XFTPNT4QW70Y2"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T22:22:21Z"
aliases = ["T-3967"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/arch/_abstraction.py"]

[[acceptance]]
text = "given an async def performing recognizable network I/O with a bare return None on a failure path, when frob check runs, then RESULT001 fires"
bound = false

[[acceptance]]
text = "given the same function returning a typani Result or raising instead, when frob check runs, then the rule stays quiet"
bound = false
+++

F-183 (T-3942 item 9). FINDING THIS WOULD HAVE CAUGHT: an async def performing network I/O (notify_admin_alert) returning None on failure, which let a caller mark alerts digested after a FAILED send. The consumer notes it violates this repo's own stated typani rule (fallible operations return Result[T, E], never a bare None/exception) that no gate currently enforces -- an intent-in-prose instance: CLAUDE.md/typani.md state the rule, nothing checks it.

Proposed rule RESULT001: an async def whose body performs recognizable network I/O (aiohttp/httpx/requests-async call, a socket send, an SMTP/webhook call) may not return None as its success/failure signal -- it must return a typani Result (or raise, if the codebase's convention is exceptions for this class). Verify scope: this is a Python-idiom rule most naturally paired with wherever the repo's own typani-adjacent lint/idiom rules already live (e.g. frob's own arch/idiom gates), not a new taint/callgraph subsystem.
