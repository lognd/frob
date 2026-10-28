+++
id = "01M5XNNH61Z437EDDB05X9CAQE"
title = "CAP: enforce may arguments (host, path, env name, binary) at call sites"
type = "security"
category = "in-progress"
priority = "high"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:08Z"
updated = "2026-10-28T18:55:24Z"
idempotency_key = "grimble-expr-args-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-bind/src/grants.rs", "crates/grimble-bind/src/model.rs", "crates/grimble-model/src/**", "crates/grimble-bind/tests/**", "crates/gob-symbols/src/call_args.rs", "crates/gob-symbols/src/lib.rs", "crates/grimble-model/src/check.rs", "crates/grimble-model/src/rules/mdl008.md", "crates/grimble-model/src/lib.rs", "crates/grimble-model/tests/may_reason.rs", "docs/design/binding.md", "docs/guides/grimble.md", "docs/design/packs.md", "docs/reference/rules/MDL008.md"]

[[acceptance]]
text = "a use whose literal argument falls outside every covering grant argument fires CAP001 naming the observed argument and the granted ones"
bound = true

[[acceptance]]
text = "a use whose argument cannot be resolved statically under an argument-scoped grant is Unresolved with reason, never clean"
bound = true

[[acceptance]]
text = "a grant argument of the wrong type for its atom is an MDL error, and trust_zones no longer exempts grants merely because they carry arguments"
bound = true
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. `may fs.read("config/**")` and `may net.connect("api.example.com")` parse, are part of the CAP005 ack identity (grant_ack.rs:55-57) and are recommended by docs/guides/grimble.md:195, but caps.rs:19 says '`may` arguments are ignored' and covers() (caps.rs:508-520) never reads them. Repro: grant fs.read("config/**"); a read of /home/u/.ssh/id_rsa in the same node is clean. grants.rs:357 trust_zones() also skips any grant with arguments ('narrow by construction'), so adding a dummy argument hides a blanket every-atom grant from grimble status. Implement per the v3 spec: typed argument schema per atom (packs.md 2 'args = path|host|name|string'), extraction of the call-site argument (literal or const-folded via gob-ir const_value), match against the grant, and Unresolved when the argument is not statically known.
