<p align="center">
  <img src="https://raw.githubusercontent.com/lognd/frob/main/docs/assets/frob-banner.svg" alt="frob: a small green goblin in an aviator cap hunched over a crystal ball of glowing rune-code. The enforcement layer for agentic development." width="100%"/>
</p>

<p align="center">
  <a href="https://pypi.org/project/frob/"><img src="https://img.shields.io/pypi/v/frob.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/frob/"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--2.0--only-blue.svg" alt="License: GPL-2.0-only"></a>
  <a href="https://github.com/lognd/frob/actions/workflows/ci.yml"><img src="https://github.com/lognd/frob/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
</p>

# frob

frob is the enforcement layer for agentic development: an obligation graph
tracks every symbol's identity, a statically-checkable ticket queue tracks
every unit of work, and a set of gates turn unaccounted-for change -- code
with no ticket, a doc that drifted, a test that vanished -- into a `frob
check` failure. Your editor or an agent's own tools navigate and edit code;
frob accounts for it.

## Highlights

- **Obligation graph.** Every symbol's identity, tests, docs, and tickets
  are tracked edges, not tribal knowledge -- `frob check` fails the moment
  one of them drifts.
- **Statically-checkable ticket queue.** Work lives in the `tickets/`
  directory, tracked in git, with declared scope, blockers, and evidence --
  not a side channel that can silently fall out of sync with the code.
- **Gates with a remedy built in.** `frob check` runs ruff, ty,
  cycle/dup/arch/bind/exports, and every enforcement gate in one pass; every
  violation message embeds the command that fixes it.
- **A comment DSL, not a wiki.** `frob:ticket`, `frob:tests`, `frob:doc`,
  `frob:invariant`, and `frob:waive` bind code to its own accounting inline,
  where a diff can't leave it behind.
- **Visible debt, never silence.** A waiver (`frob:waive RULE-ID
  reason="..."`) is an explicit, reason-carrying exception -- it shows up in
  every report instead of quietly suppressing a check.
- **An MCP server for agent hosts.** `frob serve` exposes doable tickets,
  stale docs, and graph queries as read-only tools over stdio.

## Install

```bash
uv tool install frob
```

<!-- frob:waive DOC004 reason="illustrative first-run example, output captured below in the README's own intro; not a claim tracked elsewhere" -->
```bash
frob doctor
```

```text
frob version: 0.530.0

  frob_core: available (version=unknown)
  strata_core: available (version=unknown)

all native extensions available
```

`frob doctor` is a good first command: it confirms the install and reports
whether the two native acceleration extensions (`frob-core`, `strata-core`)
are present. Both are default dependencies of a plain install; if either is
absent frob still runs, in pure-Python mode, and says so loudly rather than
degrading silently -- see docs/guides/install.md.

## Quickstart

The enforcement loop is `annotate -> check -> fix-or-waive`: bind code to a
ticket and its tests with comment directives, let `frob check` fail on
anything undeclared, then either close the gap or waive it with a reason.

```bash
frob graph build                                  # build the obligation graph cache
frob ticket new --title "Add multiply function" \
    --kind feature --scope "src/demo/calc.py"     # T-0001
frob ticket start T-0001                          # pre-work sweep, -> in-progress

# write code, bind it: `# frob:ticket T-0001` above the new symbol,
# `# frob:tests <symref>` above the test that covers it

frob check . --ticket T-0001                      # fails: undeclared change
# ... add the directives, write the test ...
frob check . --ticket T-0001                      # coverage/scope/drift clean

frob test --base main                             # run exactly the touched-set tests
frob ack src/demo/calc.py::multiply --facet sig    # acknowledge a described contract
frob ticket close T-0001                           # requires evidence + a Done report
```

See docs/guides/quickstart.md for the full walkthrough with real command
output.

## Command groups

`frob --help` groups its surface into seven verb collections -- explore,
quality, design, ops, ticket, vet, serve -- and every member also works as
its own standalone top-level command. docs/guides/command-reference.md has
the full per-group breakdown; docs/modules/cli.md carries the tier ledger
behind the grouping. The complete table is below.

<details>
<summary>Full command reference (every top-level command)</summary>

Statically bound to the live subcommand registry -- a subcommand added or
removed with no matching row here fails `frob check` (DOC005). The seven
grouped rows (`explore`/`quality`/`design`/`ops`/`ticket`/`vet`/`serve`)
are the verb collections above; everything else also works standalone.
Use `frob <verb> --help` for flags.

| Command | Description |
|---|---|
| `frob ack` | Acknowledge current digests for one or more symbol refs |
| `frob agent` | Print/export the dispatched-agent guard env |
| `frob arch` | Arch analysis: long functions, god classes, coupling |
| `frob bind` | Verify binding declarations match source signatures |
| `frob check` | Aggregate quality gate: ruff, ty, cycle/dup/arch/bind/exports, and every enforcement gate |
| `frob claude` | Sync this repo's tracked Claude config to `~/.claude/` |
| `frob clean` | Remove build/test/cache artifacts (tiered, dry-run by default) |
| `frob coverage` | Refresh `coverage.xml` / the coverage stamp, touched-set incremental by default |
| `frob cycle` | Detect import cycles in Python packages |
| `frob debt` | List outstanding `frob:debt` entries |
| `frob deploy` | Compile a host manifest into idempotent install/status/uninstall bash |
| `frob deprecated` | List outstanding `frob:deprecated` entries |
| `frob design` | Group: `sys`/`registry`/`docs`/`graph`/`exports` -- see docs/guides/command-reference.md |
| `frob docs` | Extract docstrings or search `docs/` for a file/symbol |
| `frob doctor` | Verify native extensions and report derived-state health |
| `frob dup` | Detect duplicate/clone code segments |
| `frob explore` | Group: `map`/`outline`/`xref`/`docs-search` -- see docs/guides/command-reference.md |
| `frob exports` | Generate a ready-to-paste `__init__.py` from public symbols |
| `frob fleet` | Cross-repo status/gate rollup and ticket routing over `fleet.toml` |
| `frob fmt` | Canonicalize `frob:` directive comment line-wrapping |
| `frob format` | `ruff check --fix` + `ruff format`, write mode |
| `frob gitlog` | Summarize git history filtered by conventional commit type |
| `frob graph` | Obligation graph: build the cache, query symbols, explain drift |
| `frob map` | Recursive directory tree with file sizes and line counts |
| `frob mutate` | Mutation testing: perturb a file, see which mutants survive |
| `frob narrative` | Migrate a `T-####` narrative comment block |
| `frob natives` | Build declared `[[native]]` crates via `maturin develop` |
| `frob ops` | Group: `release`/`natives`/`doctor`/`clean`/`fleet`/`deploy`/`scaffold`/`gitlog`/`stats` -- see docs/guides/command-reference.md |
| `frob outline` | Structural skeleton of a file: classes, functions, signatures |
| `frob parse` | Parse tool output (pytest/ruff/ty/clang/junit) into a compact summary |
| `frob perf` | Profile a command/test suite and inspect its heat-map |
| `frob pool` | Ratchet-pool baseline management for warn-rule findings |
| `frob profile` | Development profile (rapid/standard/fortress) status and downgrade |
| `frob quality` | Group: `check`/`test`/`dup`/`arch`/`bind`/`cycle`/`mutate`/`perf` -- see docs/guides/command-reference.md |
| `frob refactor` | Transactional symbol move/rename/split |
| `frob registry` | Exhaustiveness drift-lock over `docs/design/registry/*.yaml` |
| `frob release` | Mechanical semver from the public-API graph, plus the release gate |
| `frob scaffold` | Scaffold a new project from a registered template |
| `frob serve` | MCP stdio adapter exposing frob's enforcement queries as tools |
| `frob stats` | DORA-ish delivery measurement: queue health + commit cadence |
| `frob status` | Delta-first movement summary since the last stamped baseline |
| `frob sync-skills` | Bidirectionally sync `agents/`/`skills/` into `~/.claude/` |
| `frob sys` | strata design-model audit: model-vs-code conformance, threat/CWE/compliance/PII, deploy proofs |
| `frob test` | Select and run tests for the touched set against a base ref (or `--all`) |
| `frob ticket` | Group: the statically-checkable ticket queue -- see docs/guides/command-reference.md |
| `frob verify` | The unverified-window tracker: depth/age/quarantine status |
| `frob vet` | Group: dependency capability/CVE/supply-chain vetting -- see docs/guides/command-reference.md |
| `frob worktree` | Manage dispatched-agent git worktrees |
| `frob xref` | Find where a symbol is defined and every file that references it |

</details>

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the ticket-queue workflow,
comment-directive conventions, and the evidence/close/land dance. Please
also read the [Code of Conduct](CODE_OF_CONDUCT.md). Found a security
issue? See [SECURITY.md](SECURITY.md) -- please do not file it as a public
issue.

## More

- docs/guides/install.md -- native extensions, the T-0133 degrade contract, editable dev installs
- docs/guides/quickstart.md -- the loop above with real command output
- `docs/guides/command-reference.md` -- the seven verb groups and the full command table
- docs/modules/cli.md -- the CLI regrouping history and per-command tier ledger
- docs/ -- per-command references and module design docs
- CHANGELOG.md -- what shipped, grouped by area
