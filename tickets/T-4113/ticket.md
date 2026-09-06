---
id: T-4113
title: 'H3-3: an outbound flow''s destination must be constrained to its declared
  node, and every foreign flow needs a rate'
state: queued
kind: security
origin: human
created: '2026-09-06'
priority: critical
blocked_by:
- T-4110
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_outbound_destination.py
- tests/unit/strata/test_outbound_destination.py
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
F-307 H3-3 (verbatim, quoted at the bottom of T-4109's body). SYS100/SYS101
are file-granular: a file granted net.connect and observed connecting
satisfies the gate regardless of WHERE it connects to. The flow graph
declares backend -> media_host (a foreign node) but nothing checks that the
code's actual connection target is constrained to that declared node -- an
SSRF surface invisible to any existing rule. Two sub-findings bundled in one
report bullet, both in scope for this one leaf since they share a home (the
outbound-flow-to-foreign-node surface) and the fix's own code path (both
walk the same flow declarations):
  (a) destination-constraint: a flow X -> Y where Y is foreign requires the
      granting file to contain a host constraint bound to a config field (an
      allowlist token frob can see in code), or an explicit
      waive "SYS11x:destination-unconstrained"
  (b) missing-rate lint: an outbound flow to a foreign node with no rate
      clause, while sibling outbound flows do declare one -- this is
      narrower and cheaper than (a); implement it first as a stepping stone.

Work:
- rule (suggest SYS111) for (a): for each flow to a foreign node, verify the
  granting file's code contains a config-field-bound host/allowlist
  constraint at the connection call site; absent that, either the flow must
  carry an explicit waive naming this rule, or the finding fires
- rule (suggest SYS112, or fold into REL2xx family per this repo's existing
  outbound-rate convention if that reads more idiomatic once you are in the
  code -- decide and note which) for (b): any outbound flow to a foreign
  node with no declared rate clause is flagged

Fixture note: this concerns real network call sites (requests/httpx-shaped
code connecting to a host) that frob's own tree does not have (frob makes no
outbound network calls to foreign hosts as part of its own operation).
Build a small synthetic fixture (design nodes/flows plus a matching stub
source file with a fake outbound call) under the test directory only, with:
- must-fire (destination): a flow to a foreign node whose granting file's
  stub call site hardcodes a literal host with no config-field binding
- must-stay-quiet (destination): the same shape, but the call site reads the
  host from a config field named in an allowlist token frob can see
- must-fire (rate): an outbound flow to a foreign node with no rate= clause
  while a sibling flow in the same fixture does declare one
- must-stay-quiet (rate): every outbound flow in the fixture declares a rate
FLAG EXPLICITLY in the Done report that the fixture is synthetic, not drawn
from frob's own dogfood surface -- frob has no outbound-to-foreign-host code
path of its own to exercise this against.

frob:ticket T-4109