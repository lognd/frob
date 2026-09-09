---
id: T-4356
title: Daemon shutdown test fails Unreachable, the sole linux failure; flake or regression
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_serve_socket.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE LINUX LEG HAS ONE FAILURE LEFT AND IT MAY NOT BE DETERMINISTIC -- ESTABLISH
WHICH BEFORE FIXING ANYTHING.

MEASURED. The linux leg reports 13,860 collected, 1 failed: the daemon shutdown
test asserting that a shutdown exits and reaps its children inside a budget. The
assertion reduces to:

  assert False
    where False = Err(DaemonError.Unreachable).is_ok

So the daemon was unreachable -- the test never got far enough to measure the
budget it exists to check.

TWO REASONS TO SUSPECT INTERMITTENCY RATHER THAN A REGRESSION. First, this test
passed on the immediately preceding run of nearly the same tree; the failure
appeared without a change plausibly touching it. Second, this repository already
has a recorded flake of exactly this shape -- an unreachable-daemon failure on a
different platform, filed separately. An unreachable daemon is a startup/timing
outcome, which is the classic shape of a flake rather than a logic error.

SO THE FIRST DELIVERABLE IS A VERDICT, NOT A FIX: is this deterministic or
intermittent? Run it repeatedly, and under load, and say how many times out of how
many it fails. If it is deterministic, fix the cause. If it is intermittent, the
fix is different in kind and the rest of this applies.

IF IT IS A FLAKE, DO NOT PAPER OVER IT. This project has an explicit recorded
decision to handle flakes by fixing the specific flaky test rather than
re-running it -- an automatic rerun plugin was adopted and then deliberately
REVERTED because it turned a rare flake into a whole-suite abort. So a retry
decorator is not the answer here. Find why the daemon is unreachable: whether the
test waits long enough for startup, whether it polls or sleeps a fixed interval,
whether a previous test's daemon is still holding the socket, and whether the
budget it measures is being confused with the budget it waits.

WATCH FOR THE ADJACENT TRAP. An unreachable daemon that is reported as a failed
budget assertion is a diagnostic that names the wrong thing: the test's message
should distinguish "the daemon never came up" from "it came up and exceeded the
budget", because those have completely different causes. Improve that message
regardless of what the fix turns out to be -- it costs little and this repo has
repeatedly paid for a failure that named the wrong condition.

VERIFY on linux, where it reproduces, and quote how many runs you did and how many
failed. A single green run does not clear an intermittent failure -- that mistake
was made on the windows abort earlier today and had to be retracted.
