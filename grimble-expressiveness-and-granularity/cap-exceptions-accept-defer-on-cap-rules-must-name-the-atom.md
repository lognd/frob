+++
id = "01M5XNNHN8RQ6486GS073YMCSS"
title = "CAP exceptions: accept/defer on CAP rules must name the atom, expire, and need attester approval like grants"
type = "security"
category = "todo"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:09Z"
updated = "2026-10-27T03:15:09Z"
idempotency_key = "grimble-expr-exceptions-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/grimble-bind/src/grant_ack.rs", "crates/grimble-bind/src/rules/**", "crates/grimble-model/src/**", "crates/grimble/src/ack.rs", "crates/grimble-bind/tests/**"]

[[acceptance]]
text = "an accept/defer on CAP001 without an atom is an MDL error; one with an atom silences only that atom"
bound = false

[[acceptance]]
text = "a new or widened CAP exception is a CAP005-class finding until an attester acks it, and deleting grimble.grants.toml after it existed is reported"
bound = false

[[acceptance]]
text = "grant identity is canonicalised (aliases resolve to the canonical atom) for the ack ledger"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. A single clause `accept CAP001 because=\"ok\";` inside a node silences CAP001 for EVERY atom of that node, permanently, with no CAP005-style human ack (grant_ack.rs only tracks may grants) and, in standalone grimble check, no EXC finding about the weak reason. Repro: node bad owning py/b.py with os.system; adding the accept clause makes check clean. Also: deleting grimble.grants.toml silently disables CAP005 entirely (grant_ack.rs:13-15 'opts out'), and the ack identity uses the atom as written (grant_ack.rs:260) so 'exec' vs 'process.spawn' are different identities. Require `accept CAP001 atom=ATOM [at SELECTOR] until=DATE because=...`, put CAP exceptions into the attester ledger, and make a removed ledger a finding when grimble.lock or history shows it existed.
