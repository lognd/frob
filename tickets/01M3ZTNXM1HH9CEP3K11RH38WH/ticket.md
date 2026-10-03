+++
id = "01M3ZTNXM1HH9CEP3K11RH38WH"
title = "Plugins: path-scoped activation instead of directory packs; repository pack trust model"
type = "docs"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T02:49:49Z"
updated = "2026-10-03T02:51:44Z"
idempotency_key = "m2-plugins-trust-noscoped"
labels = ["milestone:2"]
scope = ["docs/design/**"]

[[acceptance]]
text = "Given plugins.md and packs.md, when read, then no directory-scoped pack remains, path-scoped activation and the trust model are specified, and D76 lists both decisions"
bound = false
+++

Owner decisions 2026-10-04: no directory-scoped packs (rejected: invisible per-directory behaviour, ESLint flat-config and ruff nearest-config precedent); packs activate per path from the one root config ([[packs]] paths), with grimble config --for FILE printing the effective packs and rules with provenance. Repository packs may run tier 3 (WASM) with any capability (nothing banned) under a trust model: pure by default, effects declared and scoped in the manifest, grants in grimble.toml pinned to the pack digest in the lock (a code change drops grants), per-machine trust store outside the repository (grimble trust), explicit CI trust, hard memory and time limits, wasmtime vetted. A pessimistic security audit (assume users click yes) follows in its own ticket and may revise this.
