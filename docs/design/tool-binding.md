# Tool binding: bind before own (D122)

Status: draft
Owner: gob
Decisions: D122
Audience: contributor

Provenance: accepted direction, owner question 2026-10-08: "I want to be sure
that we aren't retreading the work of things like ty and ruff ... can we
use what's already been built and pipe it through our thing?" Evidence:
notes/research/lint-reuse-research-2026-10-08.md (108 fetched sources;
aggregators qlty, Trunk, MegaLinter, reviewdog, pre-commit, rules_lint,
Sonar, Semgrep; crate publication and stability facts from crates.io and
the projects' own repositories) and the evidence-weighted catalogue
notes/research/lint-catalogue-2026-10-08.md. Extends rules.md section 4
(tool stages); epic ~224NQP4.

## 1. The boundary

frob, grimble and crunk never reimplement a single-language rule that a
maintained community tool already ships. They own only what no such tool
does: universal rules over U, architectural and cross-file rules,
cross-language rules, design-system rules, and everything tied to
tickets, evidence, leases and releases.

For a bound tool:

- It runs as a pinned subprocess through gob-exec, never as a linked
  library. A process boundary is the only interface these projects
  promise to keep: ruff's crates are published as "internal component
  crate" with no semver guarantee, ty is 0.0.x with breaking changes
  allowed between any two releases, oxlint's and Biome's linter crates
  are not published at all, clippy needs a pinned nightly with rustc-dev
  (research section 2).
- The project's own configuration is read, never rewritten: the user's
  editor, pre-commit and CI see the same findings frob does.
- Output is SARIF 2.1.0 where the tool emits it (oxlint, Biome,
  golangci-lint, Roslyn, ESLint through a formatter), else the tool's
  native JSON (ruff, ty, pyright, mypy, cargo `--message-format=json`).
  Each finding keeps the tool's id as `source_rule` beside the mapped
  frob id; frob applies baselines, ratchets, exceptions, severity,
  ticket scope and the land gate itself.
- The tool owns its fixes and its suppression comments. frob runs the
  tool's fix inside the ticket scope (tier A) instead of reimplementing
  it, and EXC017 reports a native suppression of a bound rule that has
  no frob exception.
- A tool that did not run, failed its version probe, exited with an
  undeclared status or produced unreadable output is TOOL001 Unresolved
  (rules.md 4), never a silent pass.
- Duplicate findings from two tools (or a tool and a native rule) on the
  same location and normalised id are merged; the id map declares the
  equivalences.

What frob adds over running the tools directly is the product: one
report and one gate across every tool and language, hold-the-line
baselines, exceptions with owners and expiry, ticket-scoped checks,
evidence and land gating, and loud failure when a tool silently did not
run.

## 2. Tool definitions are data

Following qlty's `plugin.toml` and Trunk's `plugin.yaml`, each bindable
tool is a data definition shipped in the std pack (plugins.md), not code:

- pinned known-good version and a version probe;
- command variants keyed by version range (tools rename flags; Trunk
  carries ruff's renames this way);
- output format and parser id (sarif, cargo-json, ruff-json, ...);
- exit-code classes: success, findings, tool error;
- config files that affect results (part of the cache key) and the
  native suppression pattern (for EXC017);
- the id map to frob ids and equivalences for dedup;
- fix command, if any, and whether it is safe to run unattended.

Results are cached by (file digest, tool version, config digest). Tools
are found on the project's own path first (`uv run ruff`, the repo's
`node_modules/.bin`, the pinned toolchain); a hermetic download of the
pinned version is a later option behind gob-trust (security.md), never
implicit.

## 3. Per ecosystem

| Ecosystem | Default binding | Notes |
|---|---|---|
| Rust | rustc and clippy through `cargo --message-format=json` | clippy only as a driver; formatters through FMT001 |
| Python | ruff (native JSON); ty or pyright for types | ty check for diagnostics; types per site through `ty server` (section 4) |
| JS/TS | oxlint (SARIF), type-aware rules opt-in | covers ESLint core, react-hooks, jsx-a11y and 59 of 61 typescript-eslint rules through tsgolint; native Windows binaries; `@oxlint/migrate` reads ESLint flat configs. ESLint stays bindable for ESLint-only plugins; Biome when a repository already uses it. Type-aware lint is outside oxlint's semver promise, hence opt-in |
| CSS | stylelint | |
| C# and Unity | Roslyn analyzers through SARIF error logs, incl. Microsoft.Unity.Analyzers and their suppressors | the unity pack (dotnet-unity.md) owns only what they do not cover |
| Go | golangci-lint (SARIF) | |
| any | typos (SPELL001), formatters in check mode (FMT001), semver checkers (VERSION001) | |

## 4. Language facts for universal rules are different

Universal and architectural rules need facts (symbols, scopes, calls,
types) inside gob's model, not findings. The boundary there is:

- Parsing stays in gob (tree-sitter and ast-grep-core, D42, D96).
  oxc_parser and oxc_semantic are the only plausible in-process
  replacements for JS/TS and are reconsidered only if tree-sitter's
  scope facts prove insufficient by measurement.
- Type facts (D119) come from the language's checker over a pinned
  protocol, failing closed to Unresolved on any version change: Python
  through `ty server` (LSP hover and inlay hints), with `dmypy inspect`
  for repositories on mypy; TypeScript through a small Node helper on
  `@typescript/typescript6` (`getTypeAtLocation`), since TypeScript 7
  shipped without an API. A spike measures latency on 1000 sites before
  either is adopted.

## 5. Consequences

- Native rule tickets for single-language checks that a bound tool
  already ships are re-scoped to a binding plus an id map, or dropped
  with a reason.
- The SARIF parser (~WAZA1EH) and the tool-definition format come first;
  every binding depends on them.
- The web profile defaults to oxlint, not ESLint (~V4KM7K8 re-scoped).
