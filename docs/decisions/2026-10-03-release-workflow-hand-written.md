# Release workflow is hand-written around `dist build`

Status: current
Owner: frob
Decisions: none
Audience: owner

- Date: 2026-10-03
- Ticket: 01M4069XFWGEFARNVXTXHT82FS

## Context

The 0.532.0 release job builds standalone `frob` archives for five targets
(releases.md 6, monorepo.md 4). cargo-dist (dist 0.32.0) can generate a
GitHub workflow with `dist init` and `dist generate`. The generated file
(measured 2026-10-03) cannot meet this repository's CI policy (cicd.md):

- no `timeout-minutes` on any job, and dist has no setting for one
  (v1 T-4470: a stuck queue held the `release` concurrency group for hours);
- `contents: write` at workflow level instead of per-job minimal permissions;
- actions pinned to tags (`actions/checkout@v6`), and the dist installer is a
  `curl | sh` of an unpinned script;
- the trigger is fixed to `**[0-9]+.[0-9]+.[0-9]+*` plus `pull_request`, not
  `frob-v*` only;
- dist maps a `PACKAGE-vVERSION` tag to a Cargo package by name, and the
  binary's package is `frob-cli`, so a `frob-v0.532.0` tag fails to parse
  (`dist plan --tag frob-v0.532.0`).

`github-action-commits` could pin the actions, but not the rest, and
`allow-dirty = ["ci"]` on a rewritten generated file would leave dist
verifying nothing.

## Decision

`.github/workflows/release.yml` is hand-written. cargo-dist still builds:
each matrix leg installs dist 0.32.0 from a checksum-verified release archive
and runs `dist build --artifacts=local --target T`, driven by
`dist-workspace.toml` (`allow-dirty = ["ci"]` records that the workflow is
ours). Jobs: `plan` (tag equals `frob-cli` version), `build` (five targets,
macOS x86_64 cross-built on `macos-latest`), `release` (the only job with
`contents: write`). `crates/frob` opts in with `[package.metadata.dist]
dist = true` because dist skips `publish = false` packages.

## Consequences

- Policy (SHA pins, permissions, timeouts, trigger, concurrency) is checked by
  actionlint, zizmor and the CI rule family, not by dist.
- Bumping dist means editing `DIST_VERSION` and four checksums in the workflow
  together with `cargo-dist-version`.
- Archive layout, naming and checksums stay dist's, so installers and the
  dev channel can reuse the same `dist build` call.
- A real tag run has not happened when this lands; see the ticket evidence.

## Alternatives considered

- Generated workflow with `github-action-commits`: still no timeouts, wrong trigger and permissions.
- Generated workflow edited by hand under `allow-dirty`: a hand-written file with extra noise.
- Renaming the package `frob-cli` to `frob` so dist's tag mapping works: wide change, unrelated to release.
