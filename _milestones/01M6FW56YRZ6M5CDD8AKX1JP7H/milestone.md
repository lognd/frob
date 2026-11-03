+++
id = "01M6FW56YRZ6M5CDD8AKX1JP7H"
version = "0.534.0"
goal = "frob safely runs third-party rules and hardens itself against what real consumer repositories exposed"
state = "open"
created = "2026-11-03T04:54:53Z"
updated = "2026-11-03T04:54:53Z"

[[criteria]]
text = "A third-party WASM rule pack runs in the sandbox, and a trap or budget overrun yields Unresolved, never silence"
bound = false

[[criteria]]
text = "An external pack is fetched by URL and tree digest, vendored, and verified against the lock"
bound = false

[[criteria]]
text = "frob mirror push and init work end to end"
bound = false

[[criteria]]
text = "Every ticket under the consumer-audit hardening epics is done or dropped with a reason"
bound = false
+++
