+++
id = "01M3ZX7WK72CJEWF38Q6ZFDTQF"
title = "Effect broker: HTTPS-only network with SSRF guards"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:35Z"
updated = "2026-10-03T03:34:35Z"
idempotency_key = "m2-sec-broker-net"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-wasm/src/broker/net.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7WAWQ1B4X0FWYCGC4SDH"

[[acceptance]]
text = "Given a request whose DNS answer is 169.254.169.254, when brokered, then it is refused unless that range is granted"
bound = false

[[acceptance]]
text = "Given a redirect to another host, when followed, then the redirect is re-checked against the grant and refused if not granted"
bound = false
+++

Implements security.md section 2.5 (network).

HTTPS only with certificate validation, redirects off by default and re-checked per hop, DNS resolved once per request and refused for loopback, link-local, private and metadata ranges unless an IP range is granted, size and time caps, exact hostnames (a *.host form is separate and loudly rendered).
