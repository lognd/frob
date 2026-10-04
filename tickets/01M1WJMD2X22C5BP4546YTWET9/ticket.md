+++
id = "01M1WJMD2X22C5BP4546YTWET9"
title = "strata: require a rate attribute on inbound writes to a carries-bearing store from an unauthenticated route"
type = "task"
category = "triage"
priority = "low"
parent = "01M1T07P0DHR8Z9D3E3PRGDJ7B"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T21:02:09Z"
aliases = ["T-4189"]
labels = ["v1-cluster:B3d", "triage:accepted"]
scope = ["src/frob/strata"]
+++

Consumer F-307/H3-2 (T-4109): retention is a time bound, not a rate bound; nothing models write amplification on carries-bearing stores. Mirror the existing outbound-flow rate requirement onto inbound writes. Not fixture-testable in frob's own tree: no carries/PII-bearing store or unauthenticated-route model exists here. Consumer-blocking: latent for us; was live for the consumer.
