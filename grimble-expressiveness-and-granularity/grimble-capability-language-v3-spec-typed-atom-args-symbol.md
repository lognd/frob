+++
id = "01M5XNNH09MD5Q6ZVH1T35301F"
title = "Grimble capability language v3 spec: typed atom args, symbol-scoped grants, never-claims, taint, expiry, environments"
type = "docs"
category = "in-progress"
priority = "high"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:08Z"
updated = "2026-10-27T03:52:07Z"
idempotency_key = "grimble-expr-spec-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness", "creates:docs/design/grimble-capabilities-v3.md"]
scope = ["docs/design/grmb-spec.md", "docs/design/binding.md", "docs/design/packs.md", "docs/design/grimble-model.md", "docs/design/grimble-capabilities-v3.md", "docs/design/README.md", "docs/README.md"]

[[acceptance]]
text = "docs/design/grimble-capabilities-v3.md exists with a grammar for typed may arguments, symbol-scoped grants, never-claims, taint rules, expiring exceptions and environment profiles, each with at least one worked example"
bound = true

[[acceptance]]
text = "the spec states, for every atom, the argument type, how a call-site argument is extracted and the verdict when it cannot be extracted (Unresolved, never a pass)"
bound = true

[[acceptance]]
text = "grmb-spec.md 4.1, binding.md 7.2 and packs.md 8.1 are reconciled with the new spec (no contradictory claims left)"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. Design-first ticket for the epic. Today a grant is `may ATOM [(strings)] [at SELECTOR]` and only ATOM plus the FILE set of SELECTOR are enforced (crates/grimble-bind/src/caps.rs:17-19, 508-520). Write the v3 capability spec covering: (1) a typed argument schema per atom (net: host glob, port/range, scheme, direction, loopback/private/public class, DNS; fs: path glob relative to repo or named roots such as tmp/home/cache, operation set read/write/create/delete/exec/metadata/symlink, stdio and fd sinks; process: binary allow-list, argv shape, env passthrough, shell=false; env: variable names and secret classes; plus clock, rng, threads, unsafe/ffi, eval/dynamic import, deserialization, reflection, db, ipc, log sinks); (2) how a call-site argument is extracted (literal, const-folded, config-derived) and what happens when it cannot be (Unresolved, never pass); (3) symbol-granular `at` and `via` (only callers of symbol S may perform C); (4) effect transitivity and effect polymorphism for wrappers, closures, trait/interface dispatch; (5) negative guarantees (`never net` on a node or selector) and code-level taint (secret label -> sink atoms); (6) exceptions with atom specificity, reason, owner and expiry, gated by attesters; (7) environments/profiles (test vs prod) and policy composition (extend/import); (8) versioning of the core vocabulary. Include the target syntax examples from the audit report section 'Target syntax' and the prior-art mapping (Deno, cap-std, Cedar, CodeQL/semgrep taint, Koka effect rows).
