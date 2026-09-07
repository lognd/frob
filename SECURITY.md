# Security Policy

## Supported versions

frob is pre-1.0 and moves fast; only the latest published release
receives security fixes.

| Version        | Supported |
|----------------|-----------|
| latest on PyPI | yes       |
| anything older | no        |

Upgrade (`uv tool upgrade frob`, or `pip install -U frob`) before filing
a report if you are not on the latest release.

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
reports should be scoped with that in mind. Concretely, `frob check` and
its subcommands, run against a repository:

- **Spawn subprocesses.** `frob check` shells out to `ruff`, `ty`, and
  (in test/coverage commands) `pytest`, plus `git` for status and diff
  queries. A report claiming argument or environment injection into any
  of these subprocess calls -- for example, a crafted file path or
  `frob.toml` value reaching a shell rather than an argv list -- is
  in scope and treated as high severity.
- **Read and write the repository it runs in.** frob reads source files,
  the `tickets/` directory, `frob.toml`, and `docs/`, and writes back to
  ticket files under `tickets/`, `.frob/` derived state, and (via `frob
  format`/`frob ticket land`/`frob release`) source files and git history
  itself. A
  report claiming frob can be made to write outside the repository root
  it was invoked against, or to escape a declared ticket `scope` via a
  crafted glob or path, is in scope.
- **Run policy queries over source.** `frob.policy` matches user-authored
  `frob.toml` globs against the tree using pathspec's gitignore dialect;
  `frob.lang` parses source with tree-sitter grammars (Python, C++,
  Kotlin, and others via `tree-sitter-language-pack`). Parsing is
  expected to be safe over arbitrary (even malformed) source -- a crafted
  input file that crashes a parser is a bug; a crafted input that
  achieves code execution during parsing is a high-severity
  vulnerability.
- **The MCP server (`frob serve`).** Exposes a subset of frob's queries
  (doable tickets, stale docs, scope/graph queries) as read-only tools
  over stdio to whatever host is configured to invoke it. A report
  claiming the server can be made to perform a write, or to answer a
  query in a way that leaks data outside the repository it was started
  against, is in scope.
- **Dependency vetting (`frob vet`).** Fetches CVE and supply-chain
  metadata about dependencies. A report about the vetting logic itself
  producing a false sense of safety (silently passing a dependency it
  should flag) is a correctness bug, not a security bug, unless it
  involves frob executing something it fetched.
- **Native extensions.** `frob-core` and `strata-core` are optional PyO3
  extensions built from `frob-core`/`strata-core` (Rust). Reports here
  should include whether the issue reproduces with frob run in
  pure-Python mode (natives absent) as well.

**Explicitly out of scope**, unless your report shows something beyond
the stated contract:

- Any effect confined to a repository you already have write access to
  and chose to run frob against -- frob is a development tool that is
  expected to read and modify the checkout it is pointed at; that is its
  job, not a vulnerability.
- Findings from `frob check`/`frob sys` being wrong (a missed violation,
  a false positive) -- these are correctness bugs, filed as a normal
  issue, unless the wrongness itself has a security consequence (for
  example, a gate that is supposed to block a dangerous pattern but can
  be trivially bypassed by construction).

If you are unsure whether something is in scope, report it anyway and
let the maintainer make the call -- a false positive costs little, a
missed report costs a lot.
