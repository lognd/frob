+++
id = "01M5XNNHV9M8HCP76TD867GGVJ"
title = "Ship the core-effects pack as versioned data: 18 atoms, parents, typed args, stdlib-derived vocabularies"
type = "task"
category = "todo"
priority = "high"
points = 13
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:09Z"
updated = "2026-10-27T03:15:09Z"
idempotency_key = "grimble-expr-coreeffects-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness", "creates:packs/core-effects/**"]
scope = ["crates/gob-ir/src/registry.rs", "crates/grimble-model/src/atoms.rs", "crates/gob-packs/**", "crates/grimble-bind/src/caps.rs", "packs/core-effects/**"]

[[acceptance]]
text = "every atom of packs.md 8.1 resolves (no MDL016) and has detector rows for Rust and Python; TypeScript rows land with the unknown-language ticket"
bound = false

[[acceptance]]
text = "the core vocabulary carries a version recorded in grimble.packs.lock and a change to it is a lock drift finding"
bound = false

[[acceptance]]
text = "METHOD_GATES and NON_PROCESS_CRATES are pack data, not Rust constants"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. packs.md 8.1 designs core-effects (fs, fs.read, fs.write, net, net.connect, net.listen, env, env.read, env.write, clock, rng, stdio, stdio.read, stdio.write, exit, process, process.spawn, unsafe; typed args; per-atom severity; Rust/Python/TypeScript rows). Reality: 7 atoms hard-coded as inventory entries (gob-ir/src/registry.rs:267-300, grimble-model/src/atoms.rs), named process.env instead of env.read/env.write, no net/process/env parents (`may net` is MDL016), no clock/rng/stdio/exit/unsafe, while docs/grimble/packs/grimble-websec.md:51 says net and db.query come from core-effects. Within existing atoms the vocabularies are thin: Rust env lacks remove_var/vars_os/current_dir/set_current_dir; Python lacks os.environ[...] subscripts, requests.post, httpx, aiohttp, http.client, socket.create_connection, http.server, uvicorn; Rust spawn lacks libc/nix exec. METHOD_GATES and NON_PROCESS_CRATES are hard-coded constants in caps.rs:49 and :94. Core atoms are not version-locked, so a grimble upgrade silently changes verdicts. Ship the pack as data under packs/core-effects with a version in grimble.packs.lock, keep process.env and exec as aliases, and derive vocabularies from the language standard libraries. Output atoms (stdio.write, stderr) must align with ~JXNJRTQ and ~JKKJPTT rather than duplicate them.
