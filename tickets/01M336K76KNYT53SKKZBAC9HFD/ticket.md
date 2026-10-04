+++
id = "01M336K76KNYT53SKKZBAC9HFD"
title = "WEBSEC318-325: CI/supply-chain hardening"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0Q1MXMXDHZ5ZJAD3XB"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5331"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_supply_chain.py", "tests/fixtures/webapp/websec3xx/supply/**", "tests/unit/test_websec_supply_chain.py", "docs/modules/webapp-websec-supply-chain.md"]

[[links]]
kind = "blocked-by"
target = "01M336K75PBAVJE0SEABECQYQV"
+++

Secrets in CI logs (workflow YAML lint for un-masked env echo), GitHub Actions pinned by tag not SHA, pull_request_target misuse (checkout of fork head + secrets use), Dockerfile running as root (no USER before entrypoint), Dockerfile :latest tag, lockfile presence/sync, typosquat edit-distance on newly added dependencies (bundled top-1000-per-ecosystem list, best-effort not exhaustive). YAML parse (reuse frob's existing GH-Actions YAML parsing if one exists, grep before adding a dependency) + Dockerfile line-scan + manifest/lockfile presence check. Fixture per rule id.
