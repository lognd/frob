---
id: T-3571
title: 'frob-arch self-join-deadlock detector: false-positive on a helper thread calling
  shutdown() on a foreign server object'
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_concurrency.py
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
Filed while triaging T-3494 (frob-arch WARN remainder after T-2379). src/frob/serve/_socketd.py:872 (_idle_monitor calling server.shutdown()) is flagged self-join-deadlock: _idle_monitor runs on a dedicated background thread (started in run_socket_daemon), while server.serve_forever() runs on run_socket_daemon's own DIFFERENT thread (src/frob/serve/_socketd.py:983). shutdown() blocking until serve_forever() notices and exits is the standard, safe socketserver idle-shutdown pattern -- not a self-join. frob:waive cannot suppress this (T-0101/_unwaivable_channel_rules in src/frob/gates/_waive.py: every frob-arch category except long-function is deliberately unwaivable -- a self-join-deadlock waiver directive would itself be flagged as ineffective, not silently accepted). _check_self_join (src/frob/arch/_concurrency.py) currently flags any function that is (a) dispatched as a pool/thread task somewhere in the module and (b) calls .join()/.shutdown()/.close() on ANY object in its own body, with no check on whether the receiver of that call is actually the SAME executor/pool the function itself was dispatched through. Narrow the detector to require that correlation (e.g. the shutdown/join receiver's name/type traces back to the dispatching Thread/Pool object, not an arbitrary domain object passed in as a parameter) before it fires -- needs a positive control (a planted GENUINE self-join, e.g. a pool worker calling its own executor.shutdown()) proven to still fire after the narrowing, per this repo's own detector-change discipline.