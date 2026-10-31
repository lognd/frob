# Security Policy

Status: current
Owner: frob
Decisions: none
Audience: user

## Supported versions

frob is pre-1.0 and moves fast; only the latest published release of the
v2 line (0.532.0 and later, the Rust rewrite) receives security fixes.
v1, the Python line that ended at 0.531.0, is not supported.

| Version                          | Supported |
|----------------------------------|-----------|
| latest v2 release (0.532.0+)     | yes       |
| v1, 0.531.0 and earlier          | no        |
| any other older v2 release       | no        |

Upgrade (`uv tool upgrade frob`, `pip install -U frob`, or the archive from
the latest [GitHub release](https://github.com/lognd/frob/releases)) before
filing a report if you are not on the latest release.

## Reporting a vulnerability

Please do not file a public GitHub issue for a suspected vulnerability.

Use one of the following, in order of preference:

1. GitHub private vulnerability reporting: open the "Security" tab on
   [lognd/frob](https://github.com/lognd/frob), then "Report a
   vulnerability". This creates a private advisory thread that only the
   maintainer and you can see.
2. Email logan@logand.app if you cannot use GitHub's reporting flow.

### What to include

- A minimal reproduction: the exact command(s) run, the repository shape
  (or a small fixture repo) that triggers the issue, and `frob --version`.
- What you expected versus what happened, and why you believe it is a
  security issue rather than a correctness bug.
- Whether the affected repository is one you control, or whether the
  issue would let one repository's frob run affect anything outside that
  repository's own checkout.

### Response expectations

The maintainer aims to acknowledge a report within 7 days. There is no
bounty program. A fix timeline depends on severity and will be discussed
with you in the private advisory thread.

## Scope notes specific to this project

frob's threat surface is genuinely larger than a typical library's, and
reports should be scoped with that in mind. The full threat model and its
invariants are in [docs/design/security.md](docs/design/security.md). In
short, the surfaces below are in scope, for `frob`, `grimble` and `crunk`
run against a repository:

- **Spawn processes.** frob runs `git`, the test runners behind
  `frob test` and `frob ticket evidence add` (nextest, pytest, vitest,
  jest, dotnet, unity, and the `command` provider), and the `[[check.tool]]`
  stages of `frob.toml`. Process spawns are limited to the crates listed in
  `[check] process_spawners` (`gob-exec` and `gob-git` here). A report
  claiming argument or environment injection into any of these -- for
  example, a crafted file path, ticket field or `frob.toml` value reaching a
  shell rather than an argv list -- is in scope and treated as high severity.
  The `command` provider takes a POSIX-quoted command line and runs no shell.
- **Read and write the repository it runs in.** frob reads source files,
  `frob.toml`, `docs/`, and the ticket ledger (on the `frob-tickets` branch
  or on your branch, per `[tickets] ref_mode`). It writes ledger events,
  `.frob/` derived state, `frob.lock`, changelog fragments and, through
  `frob work`, `frob land` and `frob release`, worktrees, branches, commits,
  tags and the base branch (`frob land --push` also pushes). A report claiming
  frob can be made to write outside the repository root it was invoked
  against, or to escape a ticket's `scope` through a crafted glob or path, is
  in scope.
- **Parse source.** frob parses source with tree-sitter grammars (the
  `gob-languages` crate, feature-gated and bounded). Parsing is expected to be
  safe over arbitrary, even malformed, source. A crafted input file that
  crashes a parser is a bug; a crafted input that achieves code execution
  during parsing is a high-severity vulnerability.
- **The MCP server (`frob serve`).** Serves the read-only verbs of the product
  as MCP tools over stdio to whatever host is configured to invoke it. A
  report claiming the server can be made to perform a write, or to answer a
  query in a way that leaks data outside the repository it was started
  against, is in scope.
- **Repository-supplied packs and configuration.** Packs, tool stages and
  `frob.toml` from a repository run with your permissions. `frob trust`
  reviews untrusted packs interactively. A report that a pack or config gets
  an effect without the review that `frob trust` and the threat model
  require is in scope.

**Explicitly out of scope**, unless your report shows something beyond
the stated contract:

- Any effect confined to a repository you already have write access to
  and chose to run frob against -- frob is a development tool that is
  expected to read and modify the checkout it is pointed at; that is its
  job, not a vulnerability.
- Findings from `frob check` being wrong (a missed violation, a false
  positive) -- these are correctness bugs, filed as a normal issue, unless
  the wrongness itself has a security consequence (for example, a gate that
  is supposed to block a dangerous pattern but can be trivially bypassed by
  construction).

If you are unsure whether something is in scope, report it anyway and
let the maintainer make the call -- a false positive costs little, a
missed report costs a lot.
