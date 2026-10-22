# crunk

Status: current
Owner: crunk
Decisions: none
Audience: user

crunk is the CSS and design-token product of the goblin family. It ships the `crunk` binary,
the `crunk-check` crate with the rule set listed in [rules/README.md](rules/README.md), the
`crunk.toml` schema ([config.md](config.md)) and a design-token exporter (`crunk tokens`).

## Verbs

| Verb | Needs `crunk.toml` | What it does |
|---|---|---|
| `crunk check` | yes | Runs the rule set and prints the `gob.sibling/1` document with `product = "crunk"` (`--json`), or a count summary. `--only`, `--fail-on`, `--base`, `--ticket-scope` as for `grimble check`. |
| `crunk doctor` | no | Reports the crunk version, the repository root and the state of `crunk.toml`. |
| `crunk tokens` | yes | Writes, previews (`--target` css, json or tailwind) or drift-checks (`--check`) the generated token files. |
| `crunk query KIND [ARG]` | yes | Read-only questions: `find NAME` (exact, then prefix, then substring, with use counts), `component NAME` (BEM structure; unknown is exit 2), `dupes [--threshold 0.6]` (sheet pairs repeating declarations), `unused` (tokens nothing references), `uses TOKEN` (`var()` sites), `color HEX` (every palette color by redmean distance), `violations [--rule ID] [--path GLOB]` (check findings, always exit 0). `--no-cache` is accepted and a no-op: queries always ingest fresh. |
| `crunk import dtcg INPUT [--store PATH]` | no | Validates a W3C DTCG token file (names, a resolvable `$type` per token, value shapes, `{a.b}` references without cycles) and stores it losslessly (default `design/tokens.dtcg.json`); `--dry-run` validates only. A bad file is a refusal (`E-DTCG`). |
| `crunk export dtcg [--store PATH] [--out PATH]` | no | Prints the stored DTCG document, or writes it to `--out`; import then export equals the input up to key order. |
| `crunk rename ID NEW` | no | Renames a `[palette]` colour or `[layers]` token (`--color-ink` to `--color-text`) and rewrites every reference in one all-or-nothing write: the `crunk.toml` key and role names, stylesheets under `css_root`, `[jsx] globs` sources, `design/**/*.toml` specs, and the regenerated token exports. Comments and unrelated strings are left alone and `--color-ink-bg` is not touched by renaming `--color-ink`. `--dry-run` previews. Refusals: `E-RENAME-NAME`, `-MISSING`, `-SAME`, `-EXISTS`, `-KIND`, `-DEF`. |
| `crunk edit FILE --patch PATCH.json` | no | Applies an RFC 6902 JSON Patch to a `*.screen.toml`, `*.component.toml` or `design/content/*.toml` file. Array elements are addressed by `id` (else `name`), e.g. `/key/home.title/text`. The patch is applied in memory, the result is re-validated by the file's schema and written atomically; the output carries a unified diff and the findings of a fresh check restricted to the touched ids. Only the keys the patch changes are rewritten: comments, spacing, key order and line endings elsewhere stay byte-identical, and a file that is not valid TOML is refused unchanged. `--dry-run` previews (no findings). Refusals: `E-EDIT-PATH`, `-READ`, `-PATCH`, `-SCHEMA`, `-WRITE`. |
| `crunk new component\|screen\|flow\|token NAME [--from FILE]` | no | Scaffolds one design file under `design/components`, `screens`, `flows` or `tokens` (`NAME.component.toml`, `NAME.screen.toml`, `NAME.flow.toml`, `NAME.toml`). NAME is a lowercase identifier (`a-z`, digits, `-`, `_`, starting with a letter, 64 characters at most). The skeleton, or the `--from` copy of an existing file of the same kind with its `name`/`id` set to NAME and `status`/`content_hash` dropped, is validated by the kind's schema before anything is written (a flow file is `name`, `nodes` as unique `screen:state` strings and `edges` with `from`, `to`, `trigger` and optional `action` and `motion`; a flow error names its code and key path, for example `E-FLOW-DANGLING at edges[1].to`, and cycles are allowed). An existing target is never overwritten; a refusal writes nothing. `--dry-run` previews. Refusals: `E-NEW-NAME`, `-EXISTS`, `-FROM`, `-PATH`, `-SCHEMA`, `-WRITE`. A file created in the instant between the existence check and the atomic rename can be replaced. |
| `crunk extract-token LITERAL [--name KEY] [--scale SCALE]` | no | Promotes a hex colour (`#abc` or `#aabbcc`, any case) to a `[palette]` token (default key `c<hex>`), or a px/rem length (`16px`, `1rem`) to a `[scales]` step (`--scale spacing` (default), `font-sizes` or `radii`; rem is stored as px via `root_font_size`), and rewrites its uses in stylesheets and JSX sources to `var(--TOKEN)`. Lengths match the same unit only (`16px` does not rewrite `1rem`) and normalise case and number form (`16PX`, `1.0rem`, `.5rem`); negatives, identifier fragments, `url(...)`, `@media`/`@container`/`@supports`/`@import` preludes, comments and strings are skipped. Durations are refused because `crunk.toml` has no duration table. `--dry-run` previews. Refusals: `E-EXTRACT-LITERAL`, `-NAME`, `-EXISTS`, `-DEF`, `-SCALE` (flag with a colour), `-DURATION` (`ms`, `s`), `-UNIT` (`%`, `em`, ...), `-ZERO`, `-NEGATIVE`. |
| `crunk map` | yes | The style inventory bucketed by `[org] buckets` order, plus strays. |
| `crunk explain NAME` | yes | Value, group, definition file, `var()` sites and utilities of one token; an unknown name exits 2 and lists close matches. |
| `crunk gallery enumerate` | yes | Opt-in (`gallery` feature): lists the spec's `(screen, state, platform)` cells; `--screen`, `--state`, `--platform` narrow it. |
| `crunk gallery render` | yes | Opt-in: renders the selected cells to PNGs under `--out` (default `gallery/renders`) and records path and SHA-256 in the manifest; a changed image clears that cell's verdict. |
| `crunk gallery triage` | no | Opt-in: serves a local contact sheet on `127.0.0.1` (`--port`, default 8765) and saves keyboard verdicts (`a` approve, `r` reject, `p` pending, arrows move, Finish saves) to the manifest as v3 with `--reviewer` and optional `--expires-in DAYS`. Blocking std-only server, no async runtime; every request needs the per-run token and a loopback `Host`. |
| `crunk gallery check` | yes | Opt-in (`cargo install crunk --features gallery`): checks `gallery/manifest.json` (`--manifest`) against the spec's cells with GALLERY001 to GALLERY005 (`--route` repeats, feeding GALLERY005). The default build refuses with `E-GALLERY-NOT-BUILT` and that remedy. |
| `crunk preview` | yes | Prints the palette, spacing, font-size and radius scales, font stacks and layers as a terminal sheet. `--color always` adds truecolor swatches; `NO_COLOR` set suppresses every escape code. |
| `crunk diff OTHER` | yes | Compares the generated tokens with those of the spec in directory (or file) `OTHER`: `+ NAME VALUE` added, `- NAME VALUE` removed, `~ NAME CURRENT -> OTHER` changed, or `no differences`. Always exit 0. |
| `crunk init [--preset default\|mono] [--force]` | no | Scaffolds `crunk.toml` (the preset plus detected `[jsx]` and `[tailwind]` sections), the `[org] buckets` directories under `css_root`, a starter `base/reset.css` and the token files; the result passes `crunk check`. An existing `crunk.toml` is a usage error (exit 2) without `--force`. |
| `crunk fix [--dry-run]` | yes | Applies the machine-applicable (Tier A) fixes of `crunk check` to stylesheets; `--dry-run` prints the diff and writes nothing. |
| `crunk review` | yes | Lists the screen states that need a human review and what changed since the last ack. |
| `crunk ack [SUBJECT]...` | yes | Records a human review of screen states (`screen/<id>/<state>` or a screen id) into `crunk.lock`; needs a terminal unless `--non-interactive`; `--dry-run` reports only. |
| `crunk rule catalog` | yes | Lists the std pack rules that `[packs]` in `crunk.toml` switches on. |
| `crunk schema` | no | Built-in: the JSON Schema of a verb's output. |

Query output is the gob envelope: `data` holds `{kind, results}` (`query`), `{buckets, strays}` (`map`)
or `{results}` (`explain`); the Python `version` field is dropped, rows are otherwise identical.
`query violations` omits unresolved findings (rules that could not run), reports line 0 for a
finding anchored at the start of a file, and words its messages as the Rust rules do. `dupes`
scores whole sheets by shared `(property, value)` declarations over the smaller sheet.

Global flags (`--json`, `--text`, `--format`, `--color`, `-v`, `--version`) come from
`gob-cli`; `--version` prints the workspace lockstep version.

## Exit codes (cli.md section 2)

| Code | Meaning here |
|---|---|
| 0 | ok |
| 1 | `check` found findings at or above `--fail-on` |
| 2 | usage error |
| 3 | `E-NO-CONFIG`: no `crunk.toml` at or above the working directory (an empty file is a valid config), or `E-CONFIG` for a malformed one |
| 4 | internal error |

## Rules

Rules are declared with `#[rule]` in `crunk-rules` (two files per rule, `src/rules/<id>.rs` and
`<id>.md`, the index generated by `cargo dev gen rules-index`); the registry page is
[rules/README.md](rules/README.md). Families and their shared metadata (check tiers, whether a
waiver applies, the severity at the release gate) are `crunk_rules::family::FAMILIES`.

- `[lint]` of `crunk.toml` sets a rule to `error`, `warn` or `off`; `off` drops the rule's findings.
- `crunk:waive RULE reason="why"` in a CSS, TSX or HTML comment suppresses that rule at the
  declaration it trails or precedes (an `accept` exception, counted in the report). A waiver with
  no reason (or a blank one) grants nothing and is WAIVE001; organisation (ORG), waiver, token and
  gallery families cannot be waived. This differs from the Python crunk, where a reasonless waiver
  still silenced its rule.
- Findings are reported ordered by file, then position, then rule.

## CI

<!-- frob:ticket 01M43ARWT173GKANZ322H41VF1 -->
Path-filtered jobs and the optional node job: [ci.md](ci.md). Moving from the Python crunk, verb by verb: [migration.md](migration.md). Switching a consumer from the Python
crunk (CI step), with the reasoned divergence list: [hullbreach-migration.md](hullbreach-migration.md).

## Boundary

No frob crate is a dependency of `crunk` or `crunk-check` (`crates/crunk/tests/boundary.rs`).

## Gallery (opt-in)

The `gallery` cargo feature of `crunk` pulls in `crunk-gallery`; it is off by default so the default
binary and the PyPI wheel stay small. The crate holds the manifest (v1 per-screen approvals, v2
per-state cells with a hashed render, v3 attributed verdicts that can expire; schemas
`docs/schemas/crunk-gallery-manifest-v{1,2,3}.json`), the cell enumeration (screens, then states,
then platforms, in spec order; `applies_to` on a state narrows its screen's, `tag:<name>` expands
to tagged platforms) and the check report (`docs/schemas/crunk-gallery-check-v1.json`).

| Rule | Severity | Meaning |
|---|---|---|
| GALLERY001 | error | a cell has no render |
| GALLERY002 | error | a render is not approved (no verdict, or pending) |
| GALLERY003 | error | an approval's `expires_at` is before today |
| GALLERY004 | error | a render was rejected |
| GALLERY005 | warn | a router route has no `[[screen]]` with that entry (query and one trailing slash ignored; `*` never needs a screen) |

Not yet verified: the manifest shapes and cell order were rebuilt from the design notes and the
shipped fixtures because the Python source is not in this checkout; the parity check is tracked as
a follow-up ticket. Rendering is separate work (render orchestration).
