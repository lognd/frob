# Migrating from the Python crunk

Status: current
Owner: crunk
Decisions: none
Audience: user

<!-- frob:ticket 01M43AVMAY5VB8K1885CDYEYV6 -->

This page is for a user of the Python crunk (`python -m crunk`, the `crunk` PyPI project) moving
to the Rust `crunk` binary. It maps every Python verb to its Rust equivalent or states that it was
removed, then lists the install, cache and dependency differences. The per-finding and parser
divergences (the reasoned list) are in [hullbreach-migration.md](hullbreach-migration.md); the
exact commands a CI step changes to are in its "CI step" table. The verbs and flags of the Rust
binary are in [README.md](README.md) (the generated verb table is
[the crunk CLI reference](../reference/cli/crunk.md); `crunk --help` and `crunk SUBCOMMAND --help` are the
authoritative flag lists); the generated rule index is [rules/README.md](rules/README.md); `crunk.toml` is in [config.md](config.md).

The Python source is not part of this repository; the Python verb list below is taken from the
calls recorded in the parity corpus (`tests/crunk-parity`, see its `PROVENANCE`).

## Verb map

| Python | Rust | Notes |
|---|---|---|
| `crunk check` | `crunk check` | Same exit codes (0 ok, 1 findings at or above `--fail-on`, 2 usage, 3 config). `--only`, `--fail-on`, `--base`, `--ticket-scope` and `--gate check\|release` are the Rust flags. |
| `crunk check --json` | `crunk check --json` | The document is the `gob.sibling/1` envelope with `product = "crunk"`; findings are in `data.findings`. `--text` and `--format` are global. |
| `crunk check --report` | removed | No Rust flag of that name: read the `--json` document, or the count summary of the text view. |
| `crunk check --contrast` | `crunk check --only CONTRAST` | Contrast is the CONTRAST rule family, judged per declared mode. |
| `crunk check --config PATH` | `crunk --cwd DIR check` | There is no config-path flag; `crunk.toml` is found at or above the working directory, and `--cwd` changes it. |
| `crunk tokens` | `crunk tokens` | Writes the generated token files. |
| `crunk tokens --format css` | `crunk tokens --target css` | `--format` is the global output format of every goblin binary. `--target` takes css, json or tailwind. |
| `crunk tokens --check` | `crunk tokens --check` | Unchanged: exits 1 naming each missing or drifted file, never writes. |
| `crunk init` | `crunk init [--preset default\|mono] [--force]` | Scaffolds `crunk.toml`, the `[org] buckets` directories, a starter `base/reset.css` and the token files. |
| `crunk query find\|component\|dupes\|unused\|uses\|color\|violations` | the same `crunk query KIND [ARG]` | Output is the gob envelope; the Python `version` field is dropped. |
| `crunk query ... --no-cache` | `crunk query ...` | `--no-cache` is accepted and does nothing: queries always ingest fresh. |
| `crunk map` | `crunk map` | Same inventory by `[org] buckets` order, plus strays. |
| `crunk explain NAME` | `crunk explain NAME` | An unknown name exits 2 and lists close matches. |
| `crunk preview` | `crunk preview` | `--color always` adds truecolor swatches; `NO_COLOR` suppresses escapes. |
| `crunk diff OTHER` | `crunk diff OTHER` | Always exit 0. |
| `crunk fix`, `crunk fix --dry-run` | `crunk fix`, `crunk fix --dry-run` | Applies the machine-applicable fixes to stylesheets only; a dry run prints the same diff and writes nothing. JSX style props are judged, never fixed. |
| `crunk cache ls`, `crunk cache prune` | removed | The cache is managed by the shared goblin cache and has no verb; see "Cache" below. |
| (none) | `crunk doctor`, `crunk schema`, `crunk serve` | Shared by every goblin binary. |
| (none) | `crunk review`, `crunk ack` | Human review of screen states, recorded in `crunk.lock`. |
| (none) | `crunk rule catalog` | The std pack rules that `[packs]` switches on. |
| the Python gallery | `crunk gallery check` | Opt-in (`cargo install crunk --features gallery`); the Playwright rendering is not ported, see "Not yet at parity" in [hullbreach-migration.md](hullbreach-migration.md). |

## Install

- The PyPI project name stays `crunk`. A `crunk` wheel is built and smoke-tested by the release
  workflow, but it is not uploaded to PyPI until the Python project is retired
  (`packaging/pypi/products.toml`), so `pip install crunk` keeps giving the Python crunk until
  then. Until that happens, install with `cargo install crunk` or the release archive.
- There is no `crk` alias: the binary and the wheel are named `crunk` and nothing in the
  repository defines a shorter name. Alias it in your shell if you want one.
- No Python environment is needed to run the Rust binary.

## Dependencies

The Python parsers (tinycss2 and the tree-sitter bindings) and their version pins are gone from
your environment. The Rust crunk parses in-process with the workspace's own pinned grammars
(`crunk-ingest`), which you neither install nor pin. Tailwind configuration is evaluated by the
node runtime only when a project uses Tailwind (`crates/crunk-tailwind`).

## Cache

The Python crunk kept its own cache and exposed it through `crunk cache`. The Rust crunk caches
parsed files by content digest in the per-user cache directory
`$XDG_CACHE_HOME/frob/cache/<repo-id>/<name>` (platform equivalents elsewhere), outside the work
tree, shared by every checkout and worktree of the repository. Keys are content digests, so the
cache never needs pruning for correctness and deleting the directory is always safe. `crunk query`
bypasses it.

## Configuration

`crunk.toml` is typed more strictly than under pydantic: `root_font_size = "16"` is rejected with
an error naming the key. A `crunk:waive` needs a reason. See the "Spec, values and tokens" table of
[hullbreach-migration.md](hullbreach-migration.md) and the generated [config.md](config.md).
