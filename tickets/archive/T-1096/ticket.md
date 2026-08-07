---
id: T-1096
title: 'daemon: subscribe/push event stream (coverage-fresh, graph-changed) over the
  socket'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
blocked_by:
- T-1092
parent: T-0321
tier: story
sprint: null
scope:
- src/frob/serve/**
- docs/modules/serve.md
- tickets.md
- tests/test_serve_events.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_serve_events.py::TestEventBus::test_publish_reaches_all_subscribers
- tests/test_serve_events.py::TestEventBus::test_publish_before_any_subscriber_is_a_noop
- tests/test_serve_events.py::TestEventBus::test_unsubscribe_wakes_blocked_consumer
- tests/test_serve_events.py::TestSubscribeAndWait::test_no_daemon_is_unreachable
- tests/test_serve_events.py::TestSubscribeAndWait::test_receives_graph_changed_after_edit
- tests/test_serve_events.py::TestSubscribeAndWait::test_receives_coverage_fresh_on_stamp_write
- tests/test_serve_events.py::TestSubscribeAndWait::test_times_out_with_no_matching_event
designated_repro_test: null
acceptance:
- text: GIVEN a client subscribed over the socket connection WHEN the daemon finishes
    an incremental graph rebuild or a coverage run completes THEN the client receives
    a graph-changed or coverage-fresh push event without polling
  evidence:
  - tests/test_serve_events.py::TestSubscribeAndWait::test_receives_graph_changed_after_edit
  - tests/test_serve_events.py::TestSubscribeAndWait::test_receives_coverage_fresh_on_stamp_write
- text: GIVEN an agent that today backgrounds make coverage and stalls waiting on
    a notification it cannot act on (docs/guides/agent-playbook.md 6b/3b, the T-0322
    stall this epic names as THE stall-killer) WHEN it instead subscribes and blocks
    on the socket THEN it receives a definitive coverage-fresh push the moment the
    run this ticket's single-flight (T-1095) resolves, in-band on the same connection,
    no separate poll loop
  evidence:
  - tests/test_serve_events.py::TestSubscribeAndWait::test_receives_coverage_fresh_on_stamp_write
  - tests/test_serve_events.py::TestSubscribeAndWait::test_times_out_with_no_matching_event
threat: null
component: null
---
Child (e) of T-0321, its named 'stall-killer'. T-0733 already runs a background poll loop (post-land re-verify every 20s, rebase-bot) but it is PULL-based: frob_daemon_status is read by a client on its own schedule, nothing is pushed. Extend the T-1092 socket protocol with a subscribe verb: a client keeps its connection open and receives async event frames (coverage-fresh, graph-changed, post-land-verdict-updated) as soon as the daemon's own state changes, instead of the client re-polling frob_daemon_status or backgrounding a subprocess. This directly replaces the make-coverage-background-and-stall failure mode T-0322 patched with foreground blocking + single-flight: with push events, a client can subscribe once and get a definitive completion signal even when someone ELSE'S single-flight run (T-1095) is what resolves it, rather than each caller blocking its own foreground call.