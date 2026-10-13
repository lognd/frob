+++
id = "01M4S1RY71ZQ2AA09ZSA3VMJ4G"
title = "frob-gh: route Client::execute through send_with_policy and graphql::parse_response, dropping its own retry loop"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-12T21:54:49Z"
updated = "2026-10-13T00:05:43Z"
scope = ["crates/frob-gh/src/client.rs", "crates/frob-gh/src/error.rs"]
+++

~05XQ12K landed policy.rs and graphql.rs standalone; client.rs still uses the old retry logic. Wire them in. Acceptance: Client::execute uses send_with_policy; existing frob-gh tests plus one test showing a GraphQL error body halts per ErrorPolicy.
