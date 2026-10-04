# Contributing to frob

frob is a Rust workspace, and since the self-host switch this repository
is checked, ticketed and landed by frob v2 built from its own tree. This
page is the workflow; the design lives in `docs/design/` and the generated
reference in `docs/reference/`.

## Quick start

- Install the pinned toolchain (`rust-toolchain.toml`), `clang` plus `mold`
  (Linux linker, see `.cargo/config.toml`) and `cargo-nextest`.
- Build the binary: `cargo build -p frob-cli`; it lands in `target/debug/frob`.
  Inside this checkout use that binary (or `cargo run -p frob-cli --`), not
  an older globally installed frob.
- `frob doctor` confirms toolchain, git, cache, config and ledger health.
- `frob check` is the gate: built-in rules plus the tool stages of
  `frob.toml` (rustfmt, clippy, generated-file freshness).
- `frob test --base <base>` runs only the tests your diff reaches and
  records the evidence.

## Ticket workflow

Tickets live in `tickets/<ulid>/` (a `ticket.md` plus one file per event)
and are written only through `frob ticket ...`, never by hand. Every
ticket has a 26-character ULID id; humans use the shortest unique suffix
as a `~handle`, and any lookup also accepts a v1 alias such as `T-0003`.
Only the full ULID is ever written into a file or a directive.

1. Find work: `frob ticket doable` lists todo tickets with no open blocker
   and a scope nobody has leased. `frob ticket brief <handle>` prints the
   description, acceptance criteria, scope and links.
2. Claim it: `frob work <handle>` leases the ticket, creates a worktree and
   branch, and moves the ticket to in-progress. Work only inside that
   worktree and only inside the ticket's `scope`. If a file outside the
   scope needs a change, widen the scope with `frob ticket update`
   (recorded as an event) or file a new ticket; never edit silently.
3. Build and test: run `cargo dev ci` before reporting; it runs locally
   exactly the checks CI runs (rustfmt, clippy for the host and
   `x86_64-pc-windows-gnu`, rustdoc with `-D warnings`, nextest
   `--profile ci`, `cargo dev gen all --check`, the pinned zizmor and
   actionlint, `frob doctor`, `frob check`, `frob test --dry-run`).
   On Windows use `cargo dev-isolated ci` (a running `gob-dev.exe` cannot be rebuilt).
   `--keep-going` runs every step, `--step <name>` one, `--list` names them.
   On a busy laptop, `CARGO_DEV_CI_REMOTE=goway cargo dev ci` runs the
   heavy steps on a goway host (see `docs/design/build-test-ci.md`
   section 4); a `GOWAY` summary line means goway failed, not the step.
   The Windows clippy step needs `rustup target add
   x86_64-pc-windows-gnu` and the MinGW C compiler (`sudo apt-get install
   -y gcc-mingw-w64-x86-64`, required by libsqlite3-sys); it checks both
   first and fails naming the install command. Steps declare such
   prerequisites in `crates/gob-dev/src/ci.rs`, and the parity test
   requires `ci.yml` to install each one. Run
   `cargo dev gen all` after any change to a rule, knob, directive or
   verb (generated pages under `docs/reference/` and `docs/schemas/`).
4. Evidence: `frob test --base <base>` records a measurement for the
   tests your diff reaches, or bind one yourself with
   `frob ticket evidence add <handle> --provider nextest --ref <filter>
   --accepts <N>`.
5. Gate: `frob check --ticket <handle>` scopes the run to your ticket.
   Green means exit 0 at `fail_on = "error"`; warnings are debt, not
   failures.
6. Land: commit, then `frob land` from the worktree. It re-verifies the
   evidence, merges onto the base branch, closes the ticket and removes
   the worktree. `frob ticket close <handle>` alone is for tickets with
   no code (decisions, triage).
7. Out-of-scope work you discover becomes a ticket, not a drive-by fix:
   `frob ticket new --title "..." --type bug --scope "..." --body "found
   while working <handle>"`, and mention its id in the commit body.

## Directive cheatsheet

Directives are comments (`//`, `#` or an HTML comment in markdown) that
bind code, tests and docs to the ledger. Ticket arguments are always full
ULIDs.

| Directive | Meaning |
|---|---|
| `frob:ticket <ulid>` | This site is accounted for by the ticket; put it on every hunk you change. |
| `frob:todo <ulid> note` | Deliberately deferred work owned by an open ticket; a bare TODO comment fails TODO001. |
| `frob:doc path#slug` | This symbol is described at that documentation anchor; the doc and code must change together. |
| `frob:tests path::Name` | This test covers that symbol (symref grammar `path::Qual.Name`). |
| `frob:invariant name` | This site upholds a named property, backed by a test. |
| `frob:accept RULE because="..."` | A permanent, reasoned exception to one rule at this site. |
| `frob:defer RULE because="..." ticket=<ulid>` | A finding parked until the named ticket pays it. |

`frob ack <symref>` records a symbol's digest in `frob.lock` so later
signature or doc drift is reported; `frob ack --help` lists the forms.

## Rules every change follows

- ASCII only in every file; no emoji.
- Commit format: `<type>(<scope>): <imperative summary, 72 chars max>`,
  then an optional body wrapped at 72 that explains why. Types: feat, fix,
  chore, refactor, test, docs, perf, ci, build. No trailing period, one
  logical change per commit, never amend a pushed commit, never skip hooks.
- No `Co-Authored-By` trailer or any other attribution line, ever.
- Every public item has a one-line doc comment (`missing_docs` is denied);
  clippy pedantic and rustdoc lints are errors in CI.
- Fallible operations return typed `Result`s; panics are for programmer
  bugs. No `std::process` outside `gob-exec` and `gob-git` (PROC001).
  Log through `tracing`, never `println!`, outside renderers.
- Update `docs/` in the same change as the code it describes.
- No new dependencies without discussion; open an issue first.
- Never read or write `.env` files or private keys.

## What CI runs

`.github/workflows/ci.yml` runs on every push and pull request: rustfmt,
clippy (`-D warnings`, host and Windows target), rustdoc (`-D warnings`),
nextest, `cargo dev gen all --check`, and on Linux the self-hosted gates
`frob doctor`, `frob check` and a dry run of
`frob test --base origin/experimental`. Each check is `cargo dev ci --step
<name>` (`cargo dev-isolated` on Windows); the argv lives in `crates/gob-dev/src/ci.rs` and a parity test
fails when the workflow and `cargo dev ci` disagree. A change that does not pass
`frob check` is not merged.

## AI-assisted contributions

AI assistance is welcome under a strict policy: say in the PR which tool
you used and how, read and understand every line you submit, and expect to
explain it in review. Unreviewed generated diffs, boilerplate that ignores
this repository, sweeping changes without a prior ticket, and tests that
only restate current behavior are not accepted. Agents follow the workflow
above exactly: `frob ticket doable`, `frob work`, stay in scope, run
`frob check --ticket` and `frob test --base` before claiming done, keep
every directive intact, report gate results honestly, and never merge
their own work. An agent-authored PR still needs a named human author.

## Reporting bugs and proposing features

Use the issue forms: [bug report](.github/ISSUE_TEMPLATE/bug_report.yml)
and [feature request](.github/ISSUE_TEMPLATE/feature_request.yml).

## License

By contributing to frob you agree that your contributions are licensed
under the project's MIT license (see [LICENSE](LICENSE)).
