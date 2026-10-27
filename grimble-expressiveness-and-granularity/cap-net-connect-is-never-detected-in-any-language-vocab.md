+++
id = "01M5XNNH36HZTBEW0DFKEM2RHP"
title = "CAP: net.connect is never detected in any language (vocab class net vs atom-name lookup)"
type = "bug"
category = "in-progress"
priority = "critical"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:08Z"
updated = "2026-10-27T05:04:48Z"
idempotency_key = "grimble-expr-netconnect-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/gob-ir/src/registry.rs", "crates/grimble-model/src/atoms.rs", "crates/grimble-bind/src/caps.rs", "crates/grimble-bind/tests/**", "design/model.grmb"]

[[acceptance]]
text = "a fixture repo using std::net::TcpStream::connect (Rust) and socket.create_connection / requests.get (Python) with no grant fires CAP001 net.connect"
bound = true

[[acceptance]]
text = "listener calls (TcpListener::bind, UdpSocket::bind) map only to net.listen, and a test asserts every registered vocabulary class names a registered atom"
bound = true
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. crates/grimble-bind/src/caps.rs:126 looks up callee_vocab(lang, atom.name), i.e. class 'net.connect', but crates/gob-ir/src/registry.rs:290-300 registers the net callees under class 'net', so net.connect has no vocabulary and is never observed. Repro: a node owning src/lib.rs with std::net::TcpStream::connect, Python socket.socket().connect or requests.get and no grant reports zero CAP001. Dogfood: crates/frob-mirror/src/github/http.rs talks to GitHub via ureq while design/model.grmb grants no net.connect and grimble check passes. The 'net' class also lists TcpListener::bind and UdpSocket::bind (listen operations) which would force a net.connect grant on listeners once wired.
