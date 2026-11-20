+++
id = "01M7X35VAR5GZ8AQ5NGPAD8WST"
title = "Audit 2026-11-20 security batch: evidence env and redaction, dir: URIs, command renderer, drive-relative names, read caps"
type = "security"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-20T18:23:23Z"
updated = "2026-11-20T23:05:22Z"
scope = ["crates/frob-evidence/**", "crates/crunk-gallery/**"]

[[acceptance]]
text = "Given an evidence command that prints its environment, when its record is stored, then secret-shaped values (KEY, TOKEN, SECRET, PASSWORD, CREDENTIAL, key: value forms, PEM blocks) are redacted and the child does not inherit the full environment"
bound = true

[[acceptance]]
text = "Given a ledger dir: URI with .. or an absolute or drive path, or a non-regular file, when fetched, then it is refused and reads are size-capped; given a crunk.toml command renderer or an artifact name like C:x, then it gets the trust notice, a relative cwd, and is refused respectively"
bound = false
+++

Findings: gob-exec runner.rs:144 EnvPolicy::Inherit, gob-log redact.rs:35-42 narrow, env.rs:34 disagrees; frob-evidence store.rs:97-109 and :190; crunk-gallery render/command.rs:50-58, render/mod.rs:32 trust notice only for web, triage/server.rs:187 and render/mod.rs artifact_name accept C:x, PNG and json read without cap (render/mod.rs:274, a11y.rs:288, boxes.rs:285). The allowed_tools allowlist matching only a program name is a design limit: document it, deny -c style flags for git and cargo if cheap.
